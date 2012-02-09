import json
from mock import Mock, patch
from unittest import TestCase

from lazythumbs.views import thumbnail

class MockCache(object):
    def __init__(self):
        self.cache = {}
    def set(self, key, value, expiration=None):
        self.cache[key] = value
    def get(self, key, default=None):
        return self.cache.get(key)

class ColdCacheThumbnailTest(TestCase):
    """ Test behavior of thumbnail view given a completely cold cache.  """
    mp = 'lazythumbs.views.%s'

    def setUp(self):
        self.tn = lambda: thumbnail(Mock(), 'img/path', 48, 48)

    def test_img_not_found(self):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        with patch(self.mp%'cache', MockCache()) as mc:
            resp = self.tn()

            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp['Content-Type'], 'image/jpeg')
            self.assertEqual(len(mc.cache.keys()), 1)
            key = mc.cache.keys()[0]
            cached = json.loads(mc.cache[key])
            self.assertEqual(cached['thumbnail_path'], '')
            self.assertEqual(cached['was_404'], True)

    @patch(mp%'os')
    def test_img_found(self, mos):
        """
        Find image on filesystem, generate thumbnail, and check for proper
        response headers and caching.
        """
        mgt = Mock(return_value=('t/p','data'))
        mos.path = Mock(return_value=True)
        with patch(self.mp%'generate_thumbnail_from_path', mgt):
            with patch(self.mp%'cache', MockCache()) as mc:
                resp = self.tn()
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp['Content-Type'], 'image/jpeg')
                self.assertEqual(resp.content, 'data')
                self.assertEqual(len(mc.cache.keys()), 1)

                key = mc.cache.keys()[0]
                cached = json.loads(mc.cache[key])
                self.assertEqual(cached['thumbnail_path'], 't/p')
                self.assertEqual(cached['was_404'], False)

class WarmCacheThumbnailTest(TestCase):
    """
    Test behavior of thumbnail view when cache is warm either with 404s or
    200s.
    """
    mp = 'lazythumbs.views.%s'
    def setUp(self):
        self.tn = lambda: thumbnail(Mock(), 'image/path', 48, 48)

    def mc_factory(self, thumbnail_path, was_404):
        """
        churn out mocked caches with a preset .get(). json-serializes
        incoming data. Also a rapper?
        """
        mc = Mock()
        ret = dict(thumbnail_path=thumbnail_path, was_404=was_404)
        jsonned= json.dumps(ret)
        mc.get = Mock(return_value=jsonned)
        mc.set = Mock()
        return mc

    @patch(mp%'generate_thumbnail_from_path')
    def test_was_404(self, mgt):
        """
        Ensure we go straight to a 404 response without setting anything new in
        cache or touching filesystem if we encounter a cached 404.
        """
        with patch(self.mp%'cache',self.mc_factory('', True)) as mc:
            resp = self.tn()
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertFalse(mgt.called)
        self.assertFalse(mc.set.called)

    @patch(mp%'ImageFile', new=Mock(side_effect=IOError))
    def test_hot_cache_cold_fs(self):
        """
        When a thumbnail is recorded as a 200 in cache but is gone from the
        file system, make sure we regenerate and return 200.
        """
        mgt = Mock(return_value=('', 'data'))
        mc = self.mc_factory('thumb/path', False)
        with patch(self.mp%'generate_thumbnail_from_path', mgt):
            with patch(self.mp%'cache', mc):
                resp = self.tn()
        self.assertTrue(mgt.called)
        self.assertEqual(resp.content, 'data')
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertEqual(resp.status_code, 200)

    def test_hot_cache_hot_fs(self):
        """
        Cached 200 case. Reads thumbnail and serves it without setting anything
        new in cache.
        """
        mif_instance = Mock()
        mif_instance.read = Mock(return_value='data')
        mif = Mock(return_value=mif_instance)
        mc = self.mc_factory('thumb/path', False)
        with patch(self.mp%'ImageFile', mif):
            with patch(self.mp%'cache', mc):
                resp = self.tn()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, 'data')
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertFalse(mc.set.called)
