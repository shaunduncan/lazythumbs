"""
    {% lazythumb image.url thumbnail '48' as img_tag%}
        <img src="{{img_tag.src}}" width="{{img_tag.width}}" height="{{img_tag.height}} />
    {% endlazythumb %}
    {% lazythumb image.url resize '150x200' %}
        <img src="{{img_tag.src}}" width="{{img_tag.width}}" height="{{img_tag.height}} />
    {% endlazythumb %}
"""
from functools import partial
from itertools import chain
import logging
import re

from django.template import TemplateSyntaxError, Library, Node, Variable
from django.conf import settings
from django.core.files.images import ImageFile

from lazythumbs.util import scale_h_to_w

SUPPORTED_ACTIONS = ['thumbnail', 'resize']

register = Library()
logger = logging.getLogger(__name__)


def quack(thing, properties, levels=[], default=None):
    to_search = [thing] + filter(None, [getattr(thing,l,None) for l in levels])
    first = lambda f, xs, d: (chain((x for x in xs if f(x)), [d])).next()

    for t in to_search:
        prop = first(partial(hasattr, t), properties, default)
        if prop is not None:
            return getattr(t, prop)

register.tag('lazythumb', lambda p,t: LazythumbNode(p,t))
class LazythumbNode(Node):
    usage = 'Expected invocation is {% url|ImageFile|Object action geometry as variable %}'
    def __init__(self, parser, token):
        bits = token.contents.split()
        try:
           _, thing, action, geometry, _, as_var = bits
        except ValueError:
            raise TemplateSyntaxError(self.usage)

        self.as_var = as_var

        if action not in SUPPORTED_ACTIONS:
            raise TemplateSyntaxError(
                'lazythumb: supported actions are %s' % SUPPORTED_ACTIONS)
        self.action = action

        self.thing = self.literal_or_var(thing)
        self.raw_geometry = self.literal_or_var(geometry)
        if type(self.raw_geometry) == type(''):
            if not self.valid_geometry(self.raw_geometry):
                raise TemplateSyntaxError(
                    "lazythumb: geometry must be like '48' or '48x100'")

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

    def parse_geometry(self, string):

    def render(self, context):
        source_width = lambda t: quack(t, ['width'], ['photo', 'image'], '')
        source_height = lambda t: quack(t, ['height'], ['photo', 'image'], '')
        def finish(src, width, height):
            context.push()
            context[self.as_var] = dict(src=src, width=width, height=height)
            output = self.nodelist.render(context)
            context.pop()
            return output

        # potentially resolve geometry
        if type(self.raw_geometry) == Variable:
            geometry = self.raw_geometry.resolve(context)
        else:
            geometry = self.raw_geometry

        # compute url
        img_object = None
        url = thing
        if type(url) == Variable:
            resolved_thing = url.resolve(context)
            if type(resolved_thing) == type(''):
                url = resolved_thing
            else:
                img_object = resolved_thing
                url = quack(img_object, ['url', 'path', 'name'], ['photo', 'image'])

        # early exit if didn't get a url or a usable geometry
        if not url || not self.valid_geometry(geometry):
            return finish(url, source_height(img_object), source_width(img_object))

        # parse geometry into width, height
        if re.match('^\d+$', geometry):
            width, height = (geometry, None)
        else: # matches \d+x\d+
            width, height = string.split('x')

        # see if we can compute height
        if not height and img_object:
            s_h = s_h or source_height(img_object)
            s_w = s_w or source_width(img_object)
            if s_h and s_w:
                height = scale_h_to_w(int(s_h), int(s_w), int(width))
            else:
                height = ''

        # if it's possible to compute source dimensions there's a potential
        # early exit here. if we can tell the new image would have the
        # same/bigger dimensions, just use the image's info and don't make a
        # special url for lazythumbs
        s_h = None
        s_w = None
        if img_object:
            s_w = source_width(img_object)
            if s_w and int(width) >= int(s_w):
                return finish(url, s_w, source_height(img_object))
            s_h = source_height(img_object)
            if s_h and int(height) >= int(s_h):
                return finish(url, s_w or source_width(img_object), s_h)

        if width and height:
            geometry = '%sx%s' % (width, height)
        else:
            geometry = width

        src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, geometry, url)
        return finish(src, width, height)
