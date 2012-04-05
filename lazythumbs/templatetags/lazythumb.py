"""
    {% lazythumb image.url thumbnail '48' as img_tag %}
        <img src="{{img_tag.src}}" width="{{img_tag.width}}" height="{{img_tag.height}} />
    {% endlazythumb %}
    {% lazythumb image.url resize '150x200' %}
        <img src="{{img_tag.src}}" width="{{img_tag.width}}" height="{{img_tag.height}} />
    {% endlazythumb %}
"""
import logging
import re
from functools import partial
from itertools import chain
from urlparse import urlparse, urljoin

from lazythumbs.util import geometry_parse

from django.template import TemplateSyntaxError, Library, Node, Variable
from django.conf import settings

# TODO this should *not* be hardcoded. it completely prevents the proper
# utilization of the subclassing feature of the renderer. A bug, imo.
SUPPORTED_ACTIONS = ['thumbnail', 'resize', 'scale']

register = Library()
logger = logging.getLogger(__name__)

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

register.tag('lazythumb', lambda p,t: LazythumbNode(p,t))
class LazythumbNode(Node):
    usage = 'Expected invocation is {% lazythumb url|ImageFile|Object action geometry as variable %}'
    def __init__(self, parser, token):
        # simple alias
        tse = lambda m: TemplateSyntaxError('lazythumb: %s' % m)
        bits = token.contents.split()
        try:
           _, thing, action, geometry, _, as_var = bits
        except ValueError:
            raise tse(self.usage)

        self.as_var = as_var

        if action not in SUPPORTED_ACTIONS:
            raise tse('supported actions are %s' % SUPPORTED_ACTIONS)
        self.action = action

        self.thing = self.literal_or_var(thing)
        self.raw_geometry = self.literal_or_var(geometry)
        if type(self.raw_geometry) == type(''):
            self.width, self.height = geometry_parse(self.action, self.raw_geometry, TemplateSyntaxError)

        self.nodelist = parser.parse(('endlazythumb',))
        parser.delete_first_token()

    # TODO surely a helper exists for this in Django
    def literal_or_var(self, thing):
        """
        Given some string, return its value without quote delimiters or a
        Variable object representing the string. For example,

        a = self.literal_or_var('"hello"')
            a is 'hello'
        a = self.literal_or_var('hello')
            a is Variable('hello')

        :param thing: A string of the form "hello", 'hello', or hello
        :returns: either a Variable or a string
        """
        literal_re = '^[\'"].*[\'"]$'
        strip_quotes = lambda s: re.sub('[\'"]', '', s)

        if re.match(literal_re, thing):
            return strip_quotes(thing)
        else:
            return Variable(thing)

    def render(self, context):
        # We use these lambdas to stay lazy: we don't ever want to look up
        # source dimensions if we can avoid it.
        source_width = lambda t: quack(t, ['width'], ['photo', 'image'], '')
        source_height = lambda t: quack(t, ['height'], ['photo', 'image'], '')
        # use a nested function to keep the logic simpler when early exiting
        def finish(src, width, height):
            context.push()
            width = int(width) if width else ''
            height = int(height) if height else ''
            context[self.as_var] = dict(src=src, width=width, height=height)
            output = self.nodelist.render(context)
            context.pop()
            return output
        early_exit = lambda u,w,h: finish(urljoin(settings.MEDIA_URL, u),w,h)

        # compute url
        img_object = None
        url = self.thing
        if type(url) == Variable:
            resolved_thing = url.resolve(context)
            if type(resolved_thing) == type(''):
                url = resolved_thing
            else:
                img_object = resolved_thing
                url = quack(img_object, ['name', 'url', 'path'], ['photo', 'image'])

        # see if we got a fully qualified url
        if url.startswith('http'):
            url = url.replace(settings.MEDIA_URL, '')
            # last ditch attempt to get something
            if url.startswith('http'):
                url = urlparse(url).path

        # extract/ensure width & height
        # It's okay to end up with '' for one of the dimensions in the case of 
        width, height = (getattr(self, a, '') for a in ('width', 'height'))
        if not (width and height):
            if type(self.raw_geometry) == Variable:
                geometry = self.raw_geometry.resolve(context)
            else:
                geometry = self.raw_geometry

            try:
                width, height = geometry_parse(self.action, geometry, ValueError)
            except ValueError, e:
                # TODO: I Think we need to set width and height or this will crash with a ValueError if we try to float ''
                logger.warn('got junk geometry variable resolution: %s' % e)
        # TODO: CODEREVIEW THIS we seem to need geometry no matter what and I think this is what it should be
        else:
            geometry = "%sx%s" %(width, height)

        # early exit if didn't get a url or a usable geometry (depending on action)
        if not url or \
                (self.action == 'resize' and not (width and height)) or \
                (self.action == 'thumbnail' and not (width or height)):
            return early_exit(url, source_width(img_object), source_height(img_object))

        # at this point we have our geo information as well as our action. if
        # it's a thumbnail, we'll need to try and scale the original image's
        # other dim to match our target dim.
        # TODO puke
        if self.action == 'thumbnail':
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
                return early_exit(url, s_w, source_height(img_object))
            s_h = source_height(img_object)
            if (s_h and height) and int(height) >= int(s_h):
                return early_exit(url, s_w or source_width(img_object), s_h)

        src = '%slt_cache/%s/%s/%s' % (getattr(settings, 'LAZYTHUMBS_URL', '/'), self.action, geometry, url)

        if settings.LAZYTHUMBS_DUMMY:
            src = 'http://placekitten.com/%s/%s' % (width, height)

        return finish(src, width, height)
