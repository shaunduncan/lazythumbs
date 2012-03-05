"""
    {% lazythumb image.url thumbnail '48' as img_tag%}
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
from urlparse import urlparse

from django.template import TemplateSyntaxError, Library, Node, Variable
from django.conf import settings
from django.core.files.images import ImageFile

SUPPORTED_ACTIONS = ['thumbnail', 'resize']

register = Library()
logger = logging.getLogger(__name__)

def geometry_parse(action, geo_str, exc):
    if action == 'thumbnail':
        width_match = re.match('^(\d+)$', geo_str)
        height_match = re.match('^x(\d+)$', geo_str)
        width, height = (
             width_match.groups[0] if width_match else None,
             height_match.groups[0] if height_match else None
        )
        if width is None and height is None:
            raise exc('must supply either a height or a width for thumbnail')

        return width, height

    if action == 'resize':
        wh_match = re.match('^(\d+)x(\d+)', geo_str)
        if not wh_match:
            raise exc('both width and height required for resize')
        return wh_match.groups()


def quack(thing, properties, levels=[], default=None):
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
    usage = 'Expected invocation is {% url|ImageFile|Object action geometry as variable %}'
    def __init__(self, parser, token):
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

    def literal_or_var(self, thing):
        literal_re = '^[\'"].*[\'"]$'
        strip_quotes = lambda s: re.sub('[\'"]', '', s)

        if re.match(literal_re, thing):
            return strip_quotes(thing)
        else:
            return Variable(thing)

    def valid_geometry(self, string):
        return re.match('^(?:\d+|\d+x\d+)$', string)

    def render(self, context):
        source_width = lambda t: quack(t, ['width'], ['photo', 'image'], '')
        source_height = lambda t: quack(t, ['height'], ['photo', 'image'], '')
        def finish(src, width, height):
            context.push()
            if width: width = int(width)
            if height: height = int(height)
            context[self.as_var] = dict(src=src, width=width, height=height)
            output = self.nodelist.render(context)
            context.pop()
            return output

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
                logger.warn('got junk geometry variable resolution: %s' % e)

        # early exit if didn't get a url or a usable geometry (depending on action)
        if not url or
                self.action == 'resize' and not (width and height) or
                self.action == 'thumbnail' and not (width or height):
            return finish(url, source_width(img_object), source_height(img_object))

        # at this point we have our geo information as well as our action. if
        # it's a thumbnail, we'll need to try and scale the original image's
        # other dim to match our target dim.
        # TODO puke
        if self.action == 'thumbnail':
            if img_object: # if we didn't get an obj there's nothing we can do
                scale = lambda a, b, c: a * (b / c)
                if not width:
                    s_w = source_width(img_object)
                    if s_w:
                        width = scale(s_w, s_h, float(height))
                if not height:
                    s_h = source_height(img_object)
                    if s_h:
                        height = scale(s_h, s_w, float(width))

        # if it's possible to compute source dimensions there's a potential
        # early exit here. if we can tell the new image would have the
        # same/bigger dimensions, just use the image's info and don't make a
        # special url for lazythumbs
        if img_object:
            s_w = source_width(img_object)
            if (s_w and width) and int(width) >= int(s_w):
                return finish(url, s_w, source_height(img_object))
            s_h = source_height(img_object)
            if (s_h and height) and int(height) >= int(s_h):
                return finish(url, s_w or source_width(img_object), s_h)

        # checking for presence of both width, height by passing a tuple to an
        # anonymous dictionary (poor python dev's switch)
        geometry_str = {
            (True, True): '%sx%s' % (width, height),
            (False, True): 'x%s' % height,
            (True, False): width
        }[(width is not None, height is not None)]

        src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, geometry, url)

        if settings.LAZYTHUMBS_DUMMY:
            src = 'http://placekitten.com/%s/%s' % (width, height)

        return finish(src, width, height)
