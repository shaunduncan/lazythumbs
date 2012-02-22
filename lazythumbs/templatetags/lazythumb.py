"""
    {% lazythumb image.url thumbnail 48 %}
    {% lazythumb image.url resize 150x200 %}
"""
from itertools import chain
import re

from django.template import TemplateSyntaxError, Variable
from django.conf import settings
from django.core.files.images import ImageFile

import lazythumbs
import pdb; pdb.set_trace()
print lazythumbs.util.scale_h_to_w
from lazythumbs.util import scale_h_to_w

register = template.Library()

SUPPORTED_ACTIONS = ['thumbnail', 'resize']

def quack(thing, properties, levels=[]):
    to_search = [thing] + filter(None, [getattr(thing,l,None) for l in levels])
    first = lambda f, xs, d: (chain((x for x in xs if f(x)), [d])).next()

    for t in to_search:
        prop = first(partial(hasattr, thing), properties, None)
        if prop is not None:
            return getattr(thing, prop)

@register.tag(lambda p,t: LazythumbNode(p,t), name='lazythumb')

class LazythumbNode(template.Node):
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

    def valid_geometry(self, string):
        return re.match('^\d+|\d+x\d+$', string)

    def parse_geometry(self, string):
        if re.match('^\d$', string):
            return int(string), None
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
            desired_width, desired_height = self.parse_geometry(geometry)

        if type(thing) == type(''):
            url = thing
        else: # look for url, width, height
            url = quack(thing, ['url', 'path', 'name'], ['photo', 'image'])
            # if d_w and d_h: pass
            # if !d_w and !d_h: grab original, this will be a no-op
            # if !d_w and d_h: something strange. use original
            # if d_w and !d_h: scale original height
            if not desired_width and not desired_height:
                # this will be a no-op; send along original dimensions
                desired_width = quack(thing, ['height'], ['photo', 'image'])
                desired_height = quack(thing, ['width'], ['photo', 'image'])
                # TODO log
                print "lazythumb: got neither width nor height making no-op"
            elif not desired_width and desired_height:
                # something strange has happened. make this a no-op and log.
                desired_width = quack(thing, ['height'], ['photo', 'image'])
                desired_height = quack(thing, ['width'], ['photo', 'image'])
                print "lazythumb: got height but not width; making no-op"
            elif desired_width and not desired_height:
                # need to get original height and scale it
                source_height = quack(thing, ['height'], ['photo', 'image'])
                source_width = quack(thing, ['width'], ['photo', 'image'])
                desired_height = scale_h_to_w(source_height,
                    source_width, desired_width)

        geometry = '%sx%s' % (desired_width, desired_height)
        if url:
            src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, geometry, url)

        img_tag = {
            'src': url or '',
            'height': height or '',
            'width': width or ''
        }

        context.push()
        context[self.as_var] = img_tag
        output = self.nodelist.render(context)
        context.pop()

        return output

    def literal_or_var(self, thing):
        literal_re = '^[\'"].*[\'"]$'
        strip_quotes = lambda s: re.sub('[\'"]', '', s)

        if re.match(literal_re, thing):
            return strip_quotes(thing)
        else:
            return Variable(thing)









#@register.tag(name="lazythumb_old")
#def lazythumb_old(parser, token):
#    tag = token.contents.split()[0]
#    try:
#        tag, url, action, geometry = token.contents.split()
#    except ValueError:
#        raise template.TemplateSyntaxError('%s requires exactly 3 arguments' % tag)
#
#    if not action in SUPPORTED_ACTIONS:
#        raise template.TemplateSyntaxError('%s expects action argument to be one of %s' % (tag, SUPPORTED_ACTIONS))
#
#    literal_re = '^[\'"].+[\'"]$'
#    strip_quotes = lambda s: re.sub('[\'"]', '', geometry)
#
#    if re.match(literal_re, geometry):
#        geometry = strip_quotes(geometry)
#        if not (re.match('^\d+x\d+', geometry) or re.match('^\d+$', geometry)):
#            raise template.TemplateSyntaxError('%s expects geometry as a single number or dimensions in the form widthxheight' % tag)
#    else:
#        geometry = template.Variable(geometry)
#
#    if re.match(literal_re, url):
#        url = strip_quotes(url)
#    else:
#        url = template.Variable(url)
#
#    return LazyThumbNode(action, url, geometry)
#
#class LazyThumbNode(template.Node):
#    def __init__(self, action, url, geometry):
#        self.action = action
#        self.url = url
#        self.geometry = geometry
#
#    def render(self, context):
#        """
#        generate an <img> tag.
#
#        :raises template.VariableDoesNotExist: if given url variable not found
#        """
#        if type(self.geometry) == template.Variable:
#            self.geometry = self.geometry.resolve(context)
#
#        if type(self.url) == template.Variable:
#            self.url = self.url.resolve(context)
#
#        img_src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, self.geometry, self.url)
#        width, height = self.geometry.split('x')
#        img_tag = '<img src="%s" width="%s" height="%s" />' % (img_src, width, height)
#
#        return img_tag
