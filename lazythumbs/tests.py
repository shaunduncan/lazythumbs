import json
from mock import Mock, patch
from unittest import TestCase

from lazythumbs.views import thumbnail

class MockCache(object):
    cache = {}
    def set(self, key, value, expiration=None):
        self.cache[key] = value
    def get(self, key, default=None):
        return self.cache.get(key)

class ColdCacheThumbnailTest(TestCase):
    """ Test behavior of thumbnail view given a completely cold cache.  """
    tn = lambda: thumbnail(Mock(), 'img/path', 48, 48)
    mp = 'lazythumbs.views.%s'

    @patch(mp%'cache', MockCache())
    def test_img_not_found(self, mc):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        resp = tn()
        self.equal(resp.status_code, 404)
        self.equal(resp.content_type, 'image/jpeg')
        self.equal(len(mc.cache.keys()), 1)
        key = mc.cache.keys()[0]
        cached = json.loads(mc.cache[key])
        self.equal(cached['thumbnail_path'], '')
        self.equal(cached['was_404'], True)

    @patch(mp%'cache', MockCache()
    @patch(mp%'generate_thumbnail_from_path',Mock(return_value=('t/p','data')))
    def test_img_found(self, mos, mc):
        """
        Find image on filesystem, generate thumbnail, and check for proper
        response headers and caching.
        """
        mos = Mock()
        mos.path = Mock(return_value=True)
        with patch(self.mp%'os', mos):
            resp = tn()
            self.equal(resp.status_code, 200)
            self.equal(resp.content_type, 'image/jpeg')
            self.equal(resp.content, 'data')
            self.equal(len(self.mc.cache.keys()), 1)

            key = mc.cache.keys()[0]
            cached = json.loads(mc.cache[key])
            self.equal(cached['thumbnail_path'], 't/p')
            self.equal(cached['was_404'], False)

class WarmCacheThumbnailTest(TestCase):
    """
    Test behavior of thumbnail view when cache is warm either with 404s or
    200s.
    """
    mp = 'lazythumbs.views.%s'
    tn = lambda ip: thumbnail(Mock(), ip, 48, 48)

    def mc_factory(cls, **kwargs):
        """
        churn out mocked caches with a preset .get(). json-serializes
        incoming data. Also a rapper?
        """
        mc = Mock()
        jsonned = json.dumps(kwargs)
        mc.get = Mock(return_value=jsonned)
        mc.set = Mock()
        return mc

    @patch(mp%'cache', mc_factory(thumbnail_path='', was_404=True))
    @patch(mp%'generate_thumbnail_from_path', Mock()))
    def test_was_404(TestCase, mgt, mc):
        """
        Ensure we go straight to a 404 response without setting anything new in
        cache or touching filesystem if we encounter a cached 404.
        """
        resp = self.tn()
        self.equal(resp.status_code, 404)
        self.equal(resp.content_type, 'image/jpeg')
        self.ok(not mgt.called)
        self.ok(not mc.set.called)

    @patch(mp%'cache', mc_factory(thumbnail_path='thumb/path', was_404=False))
    @patch(mp%'generate_thumbnail_from_path', Mock(return_value=('','data')))
    @patch(mp%'ImageFile', Mock(side_effect=IOError)
    def test_hot_cache_cold_fs(TestCase, mif, mgt, mc):
        """
        When a thumbnail is recorded as a 200 in cache but is gone from the
        file system, make sure we regenerate and return 200.
        """
        resp = self.tn()
        self.ok(mgt.called)
        self.equal(resp.content, 'data')
        self.equal(resp.content_type, 'image/jpeg')
        self.equal(resp.status_code, 200)

    @patch(mp%'cache', mc_factory(thumbnail_path='thumb/path', was_404=False))
    def test_hot_cache_hot_fs(TestCase, mc):
        """
        Basic cached 200 case. Reads thumbnail and serves it without setting
        anything new in cache.
        """
        mif = Mock()
        mif.read = mock(return_value='data')
        with patch(self.mp%'ImageFile', mif):
            resp = self.tn()
            self.equal(resp.status_code, 200)
            self.equal(resp.content, 'data')
            self.equal(resp.content_type, 'image/jpeg')
            self.ok(not mc.set.called)
