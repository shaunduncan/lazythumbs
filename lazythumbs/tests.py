from unittest import TestCase

from mock import Mock, patch

from lazythumbs.views import LazyThumbRenderer

class MockCache(object):
    def __init__(self):
        self.cache = {}
    def set(self, key, value, expiration=None):
        self.cache[key] = value
    def get(self, key, default=None):
        return self.cache.get(key)

class ColdCacheTest(TestCase):
    """ Test behavior of renderer given a completely cold cache """
    def setUp(self):
        self.renderer = LazyThumbRenderer()

    def test_thumbnail_not_found(self):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        with patch('lazythumbs.views.cache', MockCache()) as mc:
            self.renderer._render_and_save = Mock(return_value=('t/p', 'data'))
            resp = self.renderer.get(Mock(), 'thumbnail', '48', 'i/p')

            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp['Content-Type'], 'image/jpeg')
            self.assertEqual(len(mc.cache.keys()), 1)
            key = mc.cache.keys()[0]
            cached = json.loads(mc.cache[key])
            self.assertEqual(cached['rendered_path'], '')
            self.assertEqual(cached['was_404'], True)

    def test_resize_not_found(self):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        with patch('lazythumbs.views.cache', MockCache()) as mc:
            self.renderer._render_and_save = Mock(return_value=('t/p', 'data'))
            resp = self.renderer.get(Mock(), 'resize', '48x48', 'i/p')

            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp['Content-Type'], 'image/jpeg')
            self.assertEqual(len(mc.cache.keys()), 1)
            key = mc.cache.keys()[0]
            cached = json.loads(mc.cache[key])
            self.assertEqual(cached['rendered_path'], '')
            self.assertEqual(cached['was_404'], True)
