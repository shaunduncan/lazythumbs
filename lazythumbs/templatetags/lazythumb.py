"""
    {% lazythumb image.url thumbnail 48 %}
    {% lazythumb image.url resize 150x200 %}
"""
import re

from django import template

register = template.Library()

SUPPORTED_ACTIONS = ['thumbnail', 'resize']

@register.tag
def lazythumb(parser, token):
    try:
        tag, url, action, geometry = token.contents.split()
    except ValueError:
        raise template.TemplateSyntaxError('%s requires exactly 3 arguments' % tag)

    if not action in SUPPORTED_ACTIONS:
        raise template.TemplateSyntaxError('action argument must be one of %s', SUPPORTED_ACTIONS)

    if geometry.match('^\d+$', geometry):
        geometry = '%sx%s' % (geometry, geometry)
    elif not geometry.match('^\d+x\d+', geometry):
        raise template.TemplateSyntaxError('geometry must be a single number or dimensions in the form widthxheight')

    # since we only support one action, don't bother passing action. this can
    # be refactored as necessary.
    return LazyThumbNode(url, geometry)

class LazyThumbNode(template.Node):
    def __init__(self, url_var, geometry):
        self.url_var = template.Variable(url_var)
        self.geometry = geometry

    def render(self, context):
        """
        generate an <img> tag.

        :raises template.VariableDoesNotExist: if given url variable not found
        """
        url = self.url_var.resolve(context)
        width, height = self.geometry.split('x')

        img_src = '/lt/thumb/%s/%s/%s/' % (url, width, height)
        img_tag = '<img src="%s" width="%s" height="%s" />' % (img_src, width, height)

        return img_tag
