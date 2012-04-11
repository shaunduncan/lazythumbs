import re, logging
from functools import partial
from itertools import chain
from urlparse import urlparse, urljoin

from django.conf import settings

logger = logging.getLogger()

def geometry_parse(action, geo_str, exc):
    if action == 'thumbnail':
        width_match = re.match('^(\d+)$', geo_str)
        height_match = re.match('^x(\d+)$', geo_str)
        width, height = (
             width_match.groups()[0] if width_match else None,
             height_match.groups()[0] if height_match else None
        )
        if width is None and height is None:
            raise exc('must supply either a height or a width for thumbnail')

        return width, height

    if action in ('resize', 'scale'):
        wh_match = re.match('^(\d+)x(\d+)$', geo_str)
        if not wh_match:
            raise exc('both width and height required for %s' % action)
        return wh_match.groups()


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


def compute_img(thing, action, geometry):
    """ generate a src url, width and height tuple for given object or url"""

    # We use these lambdas to stay lazy: we don't ever want to look up
    # source dimensions if we can avoid it.
    source_width = lambda t: quack(t, ['width'], ['photo', 'image'], '')
    source_height = lambda t: quack(t, ['height'], ['photo', 'image'], '')
    exit = lambda u,w,h: dict(url=urljoin(settings.MEDIA_URL, u), width=w,height=h)

    # compute url
    img_object = None
    if type(thing) == type(''):
        url = thing
    else:
        img_object = thing
        url = quack(img_object, ['name', 'url', 'path'], ['photo', 'image'])

    # see if we got a fully qualified url
    if url.startswith('http'):
        url = url.replace(settings.MEDIA_URL, '')
        # last ditch attempt to get something
        if url.startswith('http'):
            url = urlparse(url).path

    # extract/ensure width & height
    # It's okay to end up with '' for one of the dimensions in the case of 
    try:
        width, height = geometry_parse(action, geometry, ValueError)
    except ValueError, e:
        # TODO: I Think we need to set width and height or this will crash with a ValueError if we try to float ''
        logger.warn('got junk geometry variable resolution: %s' % e)

    # early exit if didn't get a url or a usable geometry (depending on action)
    if not url or \
            (action == 'resize' and not (width and height)) or \
            (action == 'thumbnail' and not (width or height)):
        return exit(url, source_width(img_object), source_height(img_object))

    # at this point we have our geo information as well as our action. if
    # it's a thumbnail, we'll need to try and scale the original image's
    # other dim to match our target dim.
    # TODO puke
    if action == 'thumbnail':
        if img_object: # if we didn't get an obj there's nothing we can do
            scale = lambda a, b, c: a * (b / c)
            if not width:
                s_w = source_width(img_object)
                s_h = source_height(img_object)
                if s_w:
                    width = scale(s_w, float(height), s_h)
            if not height:
                s_w = source_width(img_object)
                s_h = source_height(img_object)
                if s_h:
                    height = scale(s_h, float(width), s_w)

    # if it's possible to compute source dimensions there's a potential
    # early exit here. if we can tell the new image would have the
    # same/bigger dimensions, just use the image's info and don't make a
    # special url for lazythumbs
    if img_object:
        s_w = source_width(img_object)
        if (s_w and width) and int(width) >= int(s_w):
            return exit(url, s_w, source_height(img_object))
        s_h = source_height(img_object)
        if (s_h and height) and int(height) >= int(s_h):
            return exit(url, s_w or source_width(img_object), s_h)

    src = '%slt_cache/%s/%s/%s' % (getattr(settings, 'LAZYTHUMBS_URL', '/'), action, geometry, url)

    if getattr(settings, 'LAZYTHUMBS_DUMMY', False):
        src = 'http://placekitten.com/%s/%s' % (width, height)

    return exit(src, width, height)
