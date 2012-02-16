import json
from unittest import TestCase

from django import template
from mock import Mock, patch

from lazythumbs.views import LazyThumbRenderer, action
from lazythumbs.templatetags.lazythumb import lazythumb, LazyThumbNode

class MockCache(object):
    def __init__(self):
        self.cache = {}
    def set(self, key, value, expiration=None):
        self.cache[key] = value
    def get(self, key, default=None):
        return self.cache.get(key)

class RenderTest(TestCase):
    """ test image rendering process """

    def test_action_decorator(self):
        class MyRenderer(LazyThumbRenderer):
            @action
            def myaction(self):
                pass

        renderer = MyRenderer()
        self.assertTrue('myaction' in renderer._allowed_actions)

    def test_render_and_save(self):
        """ """
        pass

    def test_thumbnail(self):
        """ """
        pass

    def test_resize(self):
        """ """
        pass

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


class TemplateTagTest(TestCase):
    """ Test the arg validation and output of the template tag. """
    def test_too_many_args(self):
        mt = Mock()
        mt.contents = "tag url action geometry extra"
        self.assertRaises(template.TemplateSyntaxError, lazythumb, Mock(), mt)

    def test_too_few_args(self):
        mt = Mock()
        mt.contents = "tag url action"
        self.assertRaises(template.TemplateSyntaxError, lazythumb, Mock(), mt)

    def test_invalid_geometry(self):
        mt = Mock()
        mt.contents = "tag url resize boom"
        self.assertRaises(template.TemplateSyntaxError, lazythumb, Mock(), mt)

    def test_invalid_action(self):
        mt = Mock()
        mt.contents = "tag url boom 48"
        self.assertRaises(template.TemplateSyntaxError, lazythumb, Mock(), mt)

    def test_valid_thumbnail(self):
        mt = Mock()
        mt.contents = "tag url thumbnail 48"
        node = lazythumb(Mock(), mt)
        self.assertEqual(node.geometry, '48x48')
        self.assertEqual(node.url_var.var, 'url')

    def test_valid_resize(self):
        mt = Mock()
        mt.contents = "tag url resize 150x100"
        node = lazythumb(Mock(), mt)
        self.assertEqual(node.geometry, '150x100')
        self.assertEqual(node.url_var.var, 'url')

    def test_render_success(self):
        node = LazyThumbNode('url', '100x200')
        tag_str = node.render({'url':'resolved_url'})
        self.assertEqual(tag_str,
            '<img src="/lt/thumb/100/200/resolved_url/" width="100" height="200" />')

    def test_render_no_url(self):
        node = LazyThumbNode('url', '100x200')
        self.assertRaises(template.VariableDoesNotExist, node.render, (node, {}))
