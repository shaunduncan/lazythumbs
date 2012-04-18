import logging, os, re, types
from functools import partial
from itertools import chain
from urlparse import urljoin, urlparse

from PIL import Image
from django.conf import settings

logger = logging.getLogger()



def geometry_parse(action, geometry, exc):
    """ Compute width and height from a geometry string
        This is really unpleasant the actions should themselves take care of this
        for now however everything requires a width or a height. the exc will be raises
        if neither can be parsed out of the string.

        thumbnail:  returns None for nonexistant dimensions
        resize/scale: if only one dimension is given the other is set to match it
    """

    width_match = re.match(r'^(\d+)(?:x\d+)?$', geometry)
    height_match = re.match(r'^(?:\d+)?x(\d+)$', geometry)

    if not (width_match or height_match):
        raise exc

    width = int(width_match.groups()[0]) if width_match else None
    height = int(height_match.groups()[0]) if height_match else None

    if not (width and height) and not action == 'thumbnail':
        height = width or height
        width = width or height

    return width, height


def build_geometry(action, width, height):
    """ this builds a canonical geometry so we don't create the same image twice """
    if width and height and not action == 'thumbnail':
        return "%sx%s" %(width, height)
    if not width:
        return "x%s" % height
    return str(width)


def quack(thing, properties, levels=[], default=None):
    """
    Introspects object thing for the first property in properties at its top
    level of attributes as well as at each level in levels. default is returned
    if no such property is found. For example,

    path = quack(photo_object, ['path', 'url', 'name'], ['photo'])
    will check:
        photo_object.path
        photo_object.url
        photo_object.name
        photo_object.photo.path
        photo_object.photo.url
        photo_object.photo.name
    and return the first attribute lookup that succeeds and default (which is
    None by default) otherwise.

    :param thing: An object
    :param properties: A list of properties to look up ranked in order of preference.
    :param levels: levels beyond the top level of attributes of thing to search for properties (optional, defaults to []).
    :param default: What to return if the search is unsuccessful (optional, defaults to None)

    :returns: either the a desired property or default.
    """
    if thing is None:
        return default
    to_search = [thing] + filter(None, [getattr(thing,l,None) for l in levels])
    first = lambda f, xs, d: (chain((x for x in xs if f(x)), [d])).next()

    for t in to_search:
        prop = first(partial(hasattr, t), properties, default)
        if prop:
            return getattr(t, prop)

    return default


def get_img_object_url(thing):
    img_object = None
    if type(thing) == type(''):
        url = thing
    else:
        img_object = thing
        url = quack(img_object, ['name', 'url', 'path'], ['photo', 'image'],'')

    url.replace(settings.MEDIA_URL, '')

    return img_object, url


def compute_img(thing, action, geometry):
    """ generate a src url, width and height tuple for given object or url"""

    # We use these lambdas to stay lazy: we don't ever want to look up
    # source dimensions if we can avoid it.
    source_width = lambda t: quack(t, ['width'], ['photo', 'image'])
    source_height = lambda t: quack(t, ['height'], ['photo', 'image'])
    exit = lambda u,w,h: dict(src=urljoin(settings.MEDIA_URL, u), width=str(w or '') ,height= str(h or ''))

    # compute url
    img_object = None
    if type(thing) in types.StringTypes:
        url = thing
    else:
        img_object = thing
        url = quack(img_object, ['name', 'url', 'path'], ['photo', 'image'],'')
    url = url.replace(settings.MEDIA_URL, '')

    # early exit if didn't get a url
    if not url:
        return dict(src='', width='', height='')

    #If the url still has a domain or scheme we can't thumb it
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return dict(src=url,  width=str(source_width(img_object) or ''), height=str(source_height(img_object) or ''))

    # extract/ensure width & height
    # It's okay to end up with '' for one of the dimensions in the case of thumbnail
    try:
        width, height = geometry_parse(action, geometry, ValueError)
    except ValueError, e:
        logger.warn('got junk geometry variable resolution: %s' % e)
        return exit(url, source_width(img_object), source_height(img_object))

    # at this point we have our geo information as well as our action. if
    # it's a thumbnail, we'll need to try and scale the original image's
    # other dim to match our target dim.
    # TODO puke
    if action == 'thumbnail':
        if img_object: # if we didn't get an obj there's nothing we can do
            scale = lambda a, b, c: int(a * (float(b) / c))
            if not width:
                s_w = source_width(img_object)
                s_h = source_height(img_object)
                if s_w:
                    width = scale(s_w, height, s_h)
            if not height:
                s_w = source_width(img_object)
                s_h = source_height(img_object)
                if s_h:
                    height = scale(s_h, width, s_w)

    # if it's possible to compute source dimensions there's a potential
    # early exit here. if we can tell the new image would have the
    # same/bigger dimensions, just use the image's info and don't make a
    # special url for lazythumbs
    if img_object:
        s_w = source_width(img_object)
        if (s_w and width) and width >= s_w:
            return exit(url, s_w, source_height(img_object))
        s_h = source_height(img_object)
        if (s_h and height) and height >= s_h:
            return exit(url, s_w, s_h)


    geometry = build_geometry(action, width, height)
    src = '%slt_cache/%s/%s/%s' % (getattr(settings, 'LAZYTHUMBS_URL', '/'), action, geometry, url)

    if getattr(settings, 'LAZYTHUMBS_DUMMY', False):
        src = 'http://placekitten.com/%s/%s' % (width, height)

    return exit(src, width, height)

def get_img_url(thing, action, width=None, height=None):
    """ return only the src.
        This largely exists because I'm in a hurry and
        don't want to fix things that are using this
    """
    return get_img_attrs(thing, action, width, height)['src']

def get_img_attrs(thing, action, width='', height=''):
    """ allows us to get a url easier outside of templates
        this just lets compute_img deal with invalid geometries
        TODO: compute_img should just take width/height
    """
    if width and not height:
        geometry = str(width)
    else:
        geometry = "%sx%s" %(width or '', height)
    return compute_img(thing, action, geometry)

def get_format(file_path):
    """ This gets a PIL image format string from a file name
        This should be exposed from PIL but isn't so i've copied PIL code here
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        fmt = Image.EXTENSION[ext]
    except KeyError:
        Image.init()
        fmt = Image.EXTENSION[ext]
    return fmt
