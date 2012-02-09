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
    def setUp(self):
        self.tn = lambda ip: thumbnail(Mock(), ip, 48, 48)
        self.mp = 'lazythumbs.views.%s'
        self.req = Mock()
        self.mc = MockCache()
        self.mos = Mock()
        self.mos.path = Mock()

    def test_img_not_found(self):
        with patch('lazythumbs.views.cache', self.mc):
            resp = tn('DNE')
            self.equal(resp.status_code, 404)
            self.equal(len(self.mc.cache.keys()), 1)
            key = self.mc.cache.keys()[0]
            cached = json.loads(self.mc.cache[key])
            self.equal(cached['thumbnail_path'], '')
            self.equal(cached['was_404'], True)

    def test_img_found(self, gc):
        self.mos.path.exists = Mock(return_value=True)
        mgt = Mock(return_value=('thumb/path', 'some raw data'))
        with patch(self.mp%'generate_thumbnail_from_path',mgt):
            with patch(self.mp%'cache', self.mc):
                with patch(self.mp%os, self.mos):
                    resp = tn('source/path')
                    self.equal(resp.status_code, 200)
                    self.equal(len(self.mc.cache.keys()), 1)
                    key = self.mc.cache.keys()[0]
                    cached = json.loads(self.mc.cache[key])
                    self.equal(cached['thumbnail_path'], 'thumb/path')
                    self.equal(cached['was_404'], False)

class WarmCacheThumbnailTest(TestCase):
    mp = 'lazythumbs.views.%s'
    tn = lambda ip: thumbnail(Mock(), ip, 48, 48)

    def mc_factory(cls, **kwargs):
        mc = Mock()
        jsonned = json.dumps(kwargs)
        mc.get = Mock(return_value=jsonned)
        mc.set = Mock()
        return mc

    @patch(mp%'cache', mock_cache_factory(thumbnail_path='', was_404=True))
    def test_was_404(TestCase, mc):
        resp = self.tn('img/path')
        self.equal(resp.status_code, 404)
        self.ok(not mc.set.called)

    @patch(mp%'cache', mc_factory(thumbnail_path='thumb/path', was_404=False))
    @patch(mp%'generate_thumbnail_from_path', Mock(return_value=('','')))
    @patch(mp%'ImageFile', Mock(side_effect=IOError)
    def test_hot_cache_cold_fs(TestCase, mif, mgt, mc):
        resp = self.tn('img/path')
        self.ok(mgt.called)
        self.equal(resp.status_code, 200)

    @patch(mp%'cache', mc_factory(thumbnail_path='thumb/path', was_404=False))
    def test_hot_cache_hot_fs(TestCase, mif, mc):
        mif = Mock()
        mif.read = mock(return_value='img data')
        with patch(self.mp%'ImageFile', mif):
            resp = self.tn('img/path')
            self.equal(resp.status_code, 200)
            self.equal(resp.content, 'img data')
            self.equal(resp.content_type, 'image/jpeg')
