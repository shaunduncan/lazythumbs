from unittest import TestCase

from django.template import TemplateSyntaxError, VariableDoesNotExist, Variable

from mock import Mock, patch

import json

from lazythumbs.templatetags.lazythumb import LazythumbNode, ImgAttrsNode


def node_factory(node, invocation):
    mt = Mock()
    mt.contents = invocation
    return node(Mock(), mt)


class LazythumbsTemplateTagTestCase(TestCase):
    def setUp(self):
        # NOTE this context will not push and pop so we can inspect it
        self.context = {}
        mock_cxt = Mock()
        mock_cxt.__getitem__ = lambda _, x: self.context[x]
        mock_cxt.__setitem__ = lambda _, x, y: self.context.__setitem__(x, y)

        self.mock_cxt = mock_cxt


class PseudoImageFile(object):
    def __init__(self, w, h):
        self.width = w
        self.height = h
        self.name = 'image_path'


class PseudoPhoto(object):
    def __init__(self, w, h):
        self.photo = PseudoImageFile(w, h)


class LazythumbSyntaxTest(TestCase):
    """ Test the arg validation of the template tag. """
    def test_too_many_args(self):
        mt = Mock()
        mt.contents = "tag url resize '48x48' as as_var extra"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_too_few_args(self):
        mt = Mock()
        mt.contents = "tag url resize"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_invalid_action(self):
        mt = Mock()
        mt.contents = "tag url boom '48' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_url_str(self):
        node = node_factory(LazythumbNode, "tag 'url' resize '30x30' as as_var")
        self.assertEqual(node.thing.var, "'url'")

    def test_url_var(self):
        node = node_factory(LazythumbNode, "tag url resize '30x30' as as_var")
        self.assertEqual(type(node.thing), Variable)
        self.assertEqual(node.thing.var, 'url')


class LazythumbGeometryCompileTest(TestCase):
    """ test handling of geometry argument for each action """

    def test_geo_var(self):
        node = node_factory(LazythumbNode, "tag url thumbnail geo as as_var")
        self.assertEqual(type(node.geometry), Variable)
        self.assertEqual(node.geometry.var, 'geo')


class LazythumbRenderTest(LazythumbsTemplateTagTestCase):
    """ test behavior of template tag's output """
    def setUp(self):
        super(LazythumbRenderTest, self).setUp()
        self.PseudoPhoto = PseudoPhoto
        self.PseudoImageFile = PseudoImageFile

    def test_valid_basic(self):
        """ ensure sanity in the simplest case """
        node = node_factory(LazythumbNode, "tag 'url' resize '48x50' as img_tag")
        node.render(self.mock_cxt)

        self.assertTrue('img_tag' in self.context)
        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '48')
        self.assertEqual(img_tag['height'], '50')
        self.assertTrue('url' in img_tag['src'])

    def test_resize_invalid_geo(self):
        """
        for a resize, if the geometry reference by the geometry variable is
        malformed, set width and height to None.
        """
        self.context['url'] = 'i/p'
        node = node_factory(LazythumbNode, "tag 'url' resize geo as img_tag")
        for bad_geo in ['boom', '40x', '40x40x', '40x40x40']:
            self.context['geo'] = bad_geo
            node.render(self.mock_cxt)
            img_tag = self.context['img_tag']
            self.assertEqual(img_tag['width'], '')
            self.assertEqual(img_tag['height'], '')

    def test_thumbnail_invalid_geo(self):
        """
        for a thumbnail, if the geometry reference by the geometry variable is
        malformed, set width and height to None.
        """
        node = node_factory(LazythumbNode, "tag 'url' thumbnail geo as img_tag")
        for bad_geo in ['boom', '40x40x40', '40x']:
            self.context['geo'] = bad_geo
            node.render(self.mock_cxt)
            img_tag = self.context['img_tag']
            self.assertEqual(img_tag['width'], '')
            self.assertEqual(img_tag['height'], '')

    def test_resize_valid_geo(self):
        """
        for a resize, check that width/height are set appropriately in the as
        variable for a valid geometry Variable.
        """
        self.context['geo'] = '48x50'

        node = node_factory(LazythumbNode, "tag 'url' resize geo as img")
        node.render(self.mock_cxt)

        img = self.context['img']
        self.assertEqual(img['width'], '48')
        self.assertEqual(img['height'], '50')

    def test_aresize_valid_geo(self):
        """
        for an aresize, check that width/height are set appropriately in the
        as variable for a valid geometry Variable.
        """
        self.context['geo'] = '48x50'

        node = node_factory(LazythumbNode, "tag 'url' aresize geo as img")
        node.render(self.mock_cxt)

        img = self.context['img']
        self.assertEqual(img['width'], '48')
        self.assertEqual(img['height'], '50')

    def test_aresize_no_crop_valid_geo(self):
        """
        for an aresizee_no_crop, check that width/height are set appropriately in the
        as variable for a valid geometry Variable.
        """
        self.context['geo'] = '48x50'

        node = node_factory(LazythumbNode, "tag 'url' aresizee_no_crop geo as img")
        node.render(self.mock_cxt)

        img = self.context['img']
        self.assertEqual(img['width'], '48')
        self.assertEqual(img['height'], '50')

    def test_thumbnail_and_url_valid_geo(self):
        """
        for a thumbnail, check that width and/or height is set appropriately in
        the as variable for a valid geometry Variable.
        """
        self.context['geo'] = 'x48'
        node = node_factory(LazythumbNode, "tag 'url' thumbnail geo as img")
        node.render(self.mock_cxt)
        self.assertTrue('img' in self.context)
        img = self.context['img']
        self.assertEqual(img['height'], '48')

    def test_invalid_geometry(self):
        """
        if the geometry reference by the geometry variable is
        malformed, set width and height to None.
        """
        self.context['geo'] = 'boom'
        self.context['url'] = 'i/p'
        node = node_factory(LazythumbNode, "tag 'url' resize geo as img_tag")
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], '')
        self.assertEqual(img_tag['width'], '')
        self.assertTrue('url' in img_tag['src'])

        node = node_factory(LazythumbNode, "tag 'url' thumbnail geo as img_tag")
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], '')
        self.assertEqual(img_tag['width'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_single_geo(self):
        """ test geo variable that resolves to a single number """

        node = node_factory(LazythumbNode, "tag 'url' thumbnail geo as img_tag")

        self.context['geo'] = '48'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '48')
        self.assertEqual(img_tag['height'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_double_geo(self):
        """ test geo variable that resolves to a pair of numbers """
        node = node_factory(LazythumbNode, "tag 'url' resize geo as img_tag")
        self.context['geo'] = '48x100'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '48')
        self.assertEqual(img_tag['height'], '100')
        self.assertTrue('url' in img_tag['src'])

    def test_thing_like_IF_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory(LazythumbNode, "tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '1000')
        self.assertEqual(img_tag['height'], '500')
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_IF_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory(LazythumbNode, "tag img_file thumbnail geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '50')
        self.assertEqual(img_tag['height'], '100')
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object
        """
        node = node_factory(LazythumbNode, "tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '1000')
        self.assertEqual(img_tag['height'], '500')
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object with no height. height
        should be scaled.
        """
        node = node_factory(LazythumbNode, "tag img_file thumbnail geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '50')
        self.assertEqual(img_tag['height'], '100')
        self.assertTrue('image_path' in img_tag['src'])

    def test_render_url_var_is_str(self):
        node = node_factory(LazythumbNode, "tag url_var resize '30x100' as img_tag")
        self.context['url_var'] = 'some_url'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], '30')
        self.assertEqual(img_tag['height'], '100')
        self.assertTrue('some_url' in img_tag['src'])

    def test_render_no_url(self):
        node = node_factory(LazythumbNode, "tag img_file resize '48x48' as img_tag")
        self.assertRaises(VariableDoesNotExist, node.render, (node, {}))


class ImgAttrsRenderTest(LazythumbsTemplateTagTestCase):
    """ test behavior of template tag's output """

    def test_valid_basic(self):
        """ ensure the usage works """
        node = node_factory(ImgAttrsNode, "tag img")
        self.mock_cxt['img'] = {'src': 'test.png',
                                'width': '50',
                                'height': '49'}
        output = node.render(self.mock_cxt)

        self.assertTrue('src="test.png"' in output)
        self.assertTrue('height="49"'in output)
        self.assertTrue('width="50"'in output)

    def test_templatesyntaxerror(self):
        self.assertRaises(TemplateSyntaxError, node_factory, ImgAttrsNode, "tag img foo")
