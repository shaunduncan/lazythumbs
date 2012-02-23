import json
import re
from unittest import TestCase

from django.template import TemplateSyntaxError, VariableDoesNotExist

from mock import Mock, patch

from lazythumbs.views import LazyThumbRenderer, action
from lazythumbs.templatetags.lazythumb import LazythumbNode

class MockCache(object):
    def __init__(self):
        self.cache = {}
    def set(self, key, value, expiration=None):
        self.cache[key] = value
    def get(self, key, default=None):
        return self.cache.get(key)

class MockImg(object):
    def __init__(self):
        self.called = []
        self.size = (100, 100)
    def resize(self, size, _):
        self.called.append('resize')
        self.size = size
        return self
    def crop(self, dimensions):
        self.called.append('crop')
        return self

def node_factory(invocation):
    mt = Mock()
    mt.contents = invocation
    return LazythumbNode(Mock(), mt)

class RenderTest(TestCase):
    """ test image rendering process """

    def test_action_decorator(self):
        """
        Ensure the decorator causes an action to show up in
        _allowed_actions
        """
        class MyRenderer(LazyThumbRenderer):
            @action
            def myaction(self):
                pass

        renderer = MyRenderer()
        self.assertTrue('myaction' in renderer._allowed_actions)

    def test_render_and_save(self):
        """
        Make sure the StringIO operations don't explode
        """
        class TestRenderer(LazyThumbRenderer):
            mock_img = Mock()
            @action
            def testaction(self, *args, **kwargs):
                return self.mock_img

        renderer = TestRenderer()
        renderer.fs.save = Mock()

        path, data = renderer._render_and_save('testaction', 'i/p', 1, 1)

        self.assertTrue(re.match('\w+/\w+/\w+/\w+', path))
        self.assertTrue(TestRenderer.mock_img.save.called)

    def test_thumbnail_no_height(self):
        """
        Test behavior of thumbnail action when no height is provided
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_Image = Mock()
        mock_Image.open = Mock(return_value=mock_img)
        with patch('lazythumbs.views.Image', mock_Image):
            img = renderer.thumbnail('i/p', 48)
        self.assertEqual(img.size[0], 48)
        self.assertEqual(len(mock_img.called), 2)
        self.assertTrue('resize' in mock_img.called)
        self.assertTrue('crop' in mock_img.called)

    def test_thumbnail_with_height(self):
        """
        Test behavior of thumbnail action when both width and height are
        provided.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_Image = Mock()
        mock_Image.open = Mock(return_value=mock_img)
        with patch('lazythumbs.views.Image', mock_Image):
            img = renderer.thumbnail('i/p', 48, 50)
        self.assertEqual(img.size[0], 48)
        self.assertEqual(img.size[1], 50)
        self.assertEqual(len(mock_img.called), 1)
        self.assertTrue('resize' in mock_img.called)

    def test_thumbnail_no_upscaling(self):
        """
        Ensure that upscaling is forbidden in thumbnail action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_Image = Mock()
        mock_Image.open = Mock(return_value=mock_img)
        with patch('lazythumbs.views.Image', mock_Image):
            img = renderer.thumbnail('i/p', 200, 200)

        self.assertEqual(img.size[0], 100)
        self.assertEqual(img.size[1], 100)
        self.assertEqual(len(mock_img.called), 1)
        self.assertTrue('resize' in mock_img.called)


    def test_resize(self):
        """
        Test behavior of resize action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_Image = Mock()
        mock_Image.open = Mock(return_value=mock_img)
        with patch('lazythumbs.views.Image', mock_Image):
            img = renderer.resize('i/p', 48, 50)
        self.assertEqual(img.size[0], 48)
        self.assertEqual(img.size[1], 50)
        self.assertEqual(len(mock_img.called), 1)
        self.assertTrue('resize' in mock_img.called)

    def test_resize_no_upscaling(self):
        """
        Ensure upscaling is forbidden in resize action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_Image = Mock()
        mock_Image.open = Mock(return_value=mock_img)
        with patch('lazythumbs.views.Image', mock_Image):
            img = renderer.resize('i/p', 200, 200)

        self.assertEqual(img.size[0], 100)
        self.assertEqual(img.size[1], 100)
        self.assertEqual(len(mock_img.called), 1)
        self.assertTrue('resize' in mock_img.called)

class GetViewTest(TestCase):
    """ Test behavior of LazyThumbRenderer.get """

    def mc_factory(self, rendered_path, was_404):
        """
        churn out mocked caches with a preset .get(). json-serializes
        incoming data. Also a rapper?
        """
        mc = Mock()
        ret = dict(rendered_path=rendered_path, was_404=was_404)
        jsonned = json.dumps(ret)
        mc.get = Mock(return_value=jsonned)
        mc.set = Mock()
        return mc

    def setUp(self):
        self.renderer = LazyThumbRenderer()

    def test_img_404_warm_cache(self):
        """
        Ensure we go straight to a 404 response without setting anything new in
        cache or touching filesystem if we encounter a cached 404.
        """
        self.renderer._render_and_save = Mock()
        with patch('lazythumbs.views.cache', self.mc_factory('', True)) as mc:
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertFalse(self.renderer._render_and_save.called)
        self.assertFalse(mc.set.called)

    def test_warm_cache_warm_fs(self):
        """
        Cached 200 case. Reads rendered image and serves it without setting
        anything new in cache.
        """
        mock_file = Mock()
        mock_file.read = Mock(return_value='data')
        self.renderer.fs.open = Mock(return_value=mock_file)
        self.renderer._render_and_save = Mock()
        with patch('lazythumbs.views.cache',self.mc_factory('t/p',False)) as mc:
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, 'data')
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertFalse(self.renderer._render_and_save.called)
        self.assertFalse(mc.set.called)

    def test_warm_cache_cold_fs(self):
        """
        When a thumbnail is recorded as a 200 in cache but is gone from the
        file system, make sure we regenerate and return 200.
        """
        self.renderer.fs.open = Mock(side_effect=IOError())
        self.renderer._render_and_save = Mock(return_value=('t/p', 'data'))
        with patch('lazythumbs.views.cache',self.mc_factory('t/p',False)) as mc:
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')
        self.assertTrue(self.renderer._render_and_save.called)
        self.assertFalse(mc.set.called)
        self.assertEqual(resp.content, 'data')
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertEqual(resp.status_code, 200)

    def test_img_404_cold_cache(self):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        self.renderer._render_and_save = Mock(return_value=('t/p', 'data'))
        with patch('lazythumbs.views.cache', MockCache()) as mc:
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertEqual(len(mc.cache.keys()), 1)
        key = mc.cache.keys()[0]
        cached = json.loads(mc.cache[key])
        self.assertEqual(cached['rendered_path'], '')
        self.assertEqual(cached['was_404'], True)

    def test_img_200_cold_cache(self):
        """
        Pretend we found the requested rendered image on the filesystem. Ensure
        proper response headers are set and the rendered path was cached.
        """
        self.renderer._render_and_save = Mock(return_value=('t/p', 'data'))
        self.renderer.fs.exists = Mock(return_value=True)
        with patch('lazythumbs.views.cache', MockCache()) as mc:
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertEqual(resp.content, 'data')
        self.assertEqual(len(mc.cache.keys()), 1)

        key = mc.cache.keys()[0]
        cached = json.loads(mc.cache[key])
        self.assertEqual(cached['rendered_path'], 't/p')
        self.assertEqual(cached['was_404'], False)


class TemplateTagSyntaxTest(TestCase):
    """ Test the arg validation and output of the template tag. """
    def test_too_many_args(self):
        mt = Mock()
        mt.contents = "tag url action 'geometry' as as_var extra"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_too_few_args(self):
        mt = Mock()
        mt.contents = "tag url action"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_invalid_action(self):
        mt = Mock()
        mt.contents = "tag url boom '48' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_url_str(self):
        node = node_factory("tag 'url' resize '30x30' as as_var")
        self.assertEqual(node.thing, 'url')

    def test_url_var(self):
        node = node_factory("tag url resize '30x30' as as_var")
        self.assertEqual(node.thing.var, 'url')

class TemplateTagGeometryCompileTest(TestCase):
    """ test handling of geometry argument """
    def test_invalid_geometry(self):
        mt = Mock()
        mt.contents = "tag url resize 'boom' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_single_geo_str(self):
        node = node_factory("tag url thumbnail '48' as as_var")
        self.assertEqual(node.raw_geometry, '48')

    def test_double_geo_str(self):
        node = node_factory("tag url thumbnail '50x50' as as_var")
        self.assertEqual(node.raw_geometry, '50x50')

    def test_geo_var(self):
        node = node_factory("tag url thumbnail geo as as_var")
        self.assertEqual(node.raw_geometry.var, 'geo')

    def test_invalid_3d_geo(self):
        mt = Mock()
        mt.contents = "tag url resize '43x34x34' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_invalid_nonnumber_geo(self):
        mt = Mock()
        mt.contents = "tag url resize 'boom' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

class TemplateTagRenderTest(TestCase):
    """ test behavior of template tag's output """
    def setUp(self):
        self.context = {}
        mock_cxt = Mock()
        mock_cxt.__getitem__ = lambda _,x: self.context[x]
        mock_cxt.__setitem__ = lambda _,x,y: self.context.__setitem__(x,y)

        self.mock_cxt = mock_cxt

        class PseudoImageFile(object):
            def __init__(self, w, h):
                self.width = w
                self.height = h
                self.name = 'image_path'

        class PseudoPhoto(object):
            def __init__(self, w, h):
                self.photo = PseudoImageFile(w,h)

        self.PseudoImageFile = PseudoImageFile
        self.PseudoPhoto = PseudoPhoto

    def test_valid_basic(self):
        """ ensure sanity in the simplest case """
        node = node_factory("tag 'url' thumbnail '48x48' as img_tag")
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], 48)
        self.assertEqual(img_tag['width'], 48)
        self.assertTrue('url' in img_tag['src'])

    def test_invalid_geometry(self):
        """
        if the geometry reference by the raw_geometry variable is
        malformed, set width and height to None.
        """
        node = node_factory("tag 'url' resize geo as img_tag")
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], '')
        self.assertEqual(img_tag['width'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_single_geo(self):
        """ test geo variable that resolves to a single number """
        node = node_factory("tag 'url' resize geo as img_tag")
        self.context['geo'] = '48'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 48)
        self.assertEqual(img_tag['height'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_double_geo(self):
        """ test geo variable that resolves to a pair of numbers """
        node = node_factory("tag 'url' resize geo as img_tag")
        self.context['geo'] = '48x100'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 48)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('url' in img_tag['src'])

    def test_thing_like_IF_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 1000)
        self.assertEqual(img_tag['height'], 500)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_IF_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 50)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 1000)
        self.assertEqual(img_tag['height'], 500)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object with no height. height
        should be scaled.
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 50)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('image_path' in img_tag['src'])

    def test_render_url_var_is_str(self):
        node = node_factory("tag url_var resize '30x100' as img_tag")
        self.context['url_var'] = 'some_url'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 30)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('some_url' in img_tag['src'])

    def test_render_no_url(self):
        node = node_factory("tag img_file resize '48x48' as img_tag")
        self.assertRaises(VariableDoesNotExist, node.render, (node, {}))
