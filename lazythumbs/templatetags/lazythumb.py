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
import json

from django.template import TemplateSyntaxError, Library, Node, Variable
from lazythumbs.util import compute_img, get_attr_string, get_placeholder_url, get_source_img_attrs
from lazythumbs.views import LazyThumbRenderer


SUPPORTED_ACTIONS = LazyThumbRenderer().allowed_actions

register = Library()
logger = logging.getLogger()

register.tag('lazythumb', lambda p, t: LazythumbNode(p, t))
class LazythumbNode(Node):
    usage = 'Expected invocation is {% lazythumb url|ImageFile|Object action geometry [**kwargs] as variable %}'

    def __init__(self, parser, token):
        # simple alias
        tse = lambda m: TemplateSyntaxError('lazythumb: %s' % m)
        bits = token.contents.split()

        try:
            # Everything before kwargs
            _, thing, action, geometry = bits[0:4]
            # as variable (and the word 'as' itself)
            if bits[-2] != 'as':
                raise ValueError("Expected 'as' before assignment variable.")
            as_var = bits[-1]
            # Keyword arguments
            self.kwargs = {}
            raw_kwargs = bits[4:-2]
            for kwarg in raw_kwargs:
                kwarg_name, kwarg_value = kwarg.split('=')
                self.kwargs[kwarg_name] = Variable(kwarg_value)
        except ValueError:
            raise tse(self.usage)

        self.as_var = as_var

        if action not in SUPPORTED_ACTIONS:
            raise tse('supported actions are %s' % SUPPORTED_ACTIONS)
        self.action = action

        self.thing = Variable(thing)
        self.geometry = Variable(geometry)

        self.nodelist = parser.parse(('endlazythumb',))
        parser.delete_first_token()

    def render(self, context):

        thing = self.thing.resolve(context)
        action = self.action
        geometry = self.geometry.resolve(context)

        options = {}
        for k, v in self.kwargs.items():
            options[k] = v.resolve(context)

        context.push()
        context[self.as_var] = compute_img(thing, action, geometry, options)
        output = self.nodelist.render(context)
        context.pop()
        return output


register.tag('img_attrs', lambda p, t: ImgAttrsNode(p, t))
class ImgAttrsNode(Node):
    usage = 'Expected invocation is {% img_attrs img %} where img is the img attrs set by the lazythumb tag'

    def __init__(self, parser, token):
        try:
            _, img = token.contents.split()
        except ValueError:
            raise TemplateSyntaxError('img_attrs: %s' % self.usage)
        self.img_var = Variable(img)

    def render(self, context):
        return get_attr_string(self.img_var.resolve(context))
