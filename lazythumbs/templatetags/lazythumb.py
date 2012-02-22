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


def quack(thing, properties, levels=[]):
    to_search = [thing] + filter(None, [getattr(thing,l,None) for l in levels])
    first = lambda f, xs, d: (chain((x for x in xs if f(x)), [d])).next()

    for t in to_search:
        prop = first(partial(hasattr, t), properties, None)
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
        if re.match('^\d+$', string):
            return string, None
        else: # matches \d+x\d+
            return string.split('x')

    def render(self, context):
        # handle thing
        # thing is either a string (url), an ImageFile, or some random object that supports hasattr, getattr.
        # what's our target? src, width, height.
        if type(self.raw_geometry) == Variable:
            geometry = self.raw_geometry.resolve(context)
            if not self.valid_geometry(geometry):
                desired_width = None
                desired_height = None
            else:
                desired_width, desired_height = self.parse_geometry(geometry)
        else:
            desired_width, desired_height = self.parse_geometry(self.raw_geometry)

        thing = self.thing
        if type(thing) == type(''):
            url = thing
        else: # look for url, width, height
            thing = self.thing.resolve(context)
            if type(thing) == type(''):
                url = thing
            else:
                url = quack(thing, ['url', 'path', 'name'], ['photo', 'image'])
            # if d_w and d_h: pass
            # if !d_w and !d_h: grab original, this will be a no-op
            # if !d_w and d_h: something strange. use original (no-op case)
            # if d_w and !d_h: scale original height
            if not desired_width and not desired_height:
                # this will be a no-op; send along original dimensions
                desired_width = quack(thing, ['width'], ['photo', 'image'])
                desired_height = quack(thing, ['height'], ['photo', 'image'])
                logging.warn("lazythumb: got neither width nor height making no-op")
            elif not desired_width and desired_height:
                # something strange has happened. make this a no-op and log.
                desired_width = quack(thing, ['width'], ['photo', 'image'])
                desired_height = quack(thing, ['height'], ['photo', 'image'])
                logging.warn("lazythumb: got height but not width; making no-op")
            elif desired_width and not desired_height:
                # need to get original height and scale it
                source_width = quack(thing, ['width'], ['photo', 'image'])
                source_height = quack(thing, ['height'], ['photo', 'image'])
                desired_height = scale_h_to_w(source_height,
                    source_width, desired_width)

        geometry = '%sx%s' % (desired_width, desired_height)
        if url:
            src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, geometry, url)

        img_tag = {
            'src': src or '',
            'height': int(desired_height) if desired_height else '',
            'width': int(desired_width) if desired_width else ''
        }

        context.push()
        context[self.as_var] = img_tag
        output = self.nodelist.render(context)
        context.pop()

        return output
