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

from django.template import TemplateSyntaxError, Library, Node, Variable
from lazythumbs.util import compute_img


# TODO this should *not* be hardcoded. it completely prevents the proper
# utilization of the subclassing feature of the renderer. A bug, imo.
SUPPORTED_ACTIONS = ['thumbnail', 'resize', 'scale']

register = Library()
logger = logging.getLogger()

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
        self.geometry = self.literal_or_var(geometry)

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

        thing = self.thing
        if type(thing) == Variable:
            thing = thing.resolve(context)
        action = self.action
        if type(action) == Variable:
            action = action.resolve(context)
        geometry = self.geometry
        if type(geometry) == Variable:
            geometry = geometry.resolve(context)

        context.push()
        context[self.as_var] = compute_img(thing, action, geometry)
        output = self.nodelist.render(context)
        context.pop()
        return output
