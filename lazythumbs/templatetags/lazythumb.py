"""
    {% lazythumb image.url thumbnail 48 %}
    {% lazythumb image.url resize 150x200 %}
"""
import re

from django import template
from django.conf import settings

register = template.Library()

SUPPORTED_ACTIONS = ['thumbnail', 'resize']

@register.tag
def lazythumb(parser, token):
    tag = token.contents.split()[0]
    try:
        tag, url, action, geometry = token.contents.split()
    except ValueError:
        raise template.TemplateSyntaxError('%s requires exactly 3 arguments' % tag)


    if not re.match('^[\'"].+[\'"]$', geometry):
        raise template.TemplateSyntaxError('%s expected string literal for gemoetry' % tag)

    geometry = re.sub('[\'"]', '', geometry)

    if not action in SUPPORTED_ACTIONS:
        raise template.TemplateSyntaxError('%s expects action argument to be one of %s' % (tag, SUPPORTED_ACTIONS))

    if re.match('^\d+$', geometry):
        geometry = '%sx%s' % (geometry, geometry)
    elif not re.match('^\d+x\d+', geometry):
        raise template.TemplateSyntaxError('%s expects geometry as a single number or dimensions in the form widthxheight' % tag)

    return LazyThumbNode(action, url, geometry)

class LazyThumbNode(template.Node):
    def __init__(self, action, url_var, geometry):
        self.action = action
        self.url_var = template.Variable(url_var)
        self.geometry = geometry

    def render(self, context):
        """
        generate an <img> tag.

        :raises template.VariableDoesNotExist: if given url variable not found
        """
        url = self.url_var.resolve(context)

        img_src = '%s/lt/%s/%s/%s/' % (settings.LAZYTHUMBS_URL, self.action, self.geometry, url)
        width, height = self.geometry.split('x')
        img_tag = '<img src="%s" width="%s" height="%s" />' % (img_src, width, height)

        return img_tag
