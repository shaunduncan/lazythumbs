from unittest import TestCase

from mock import Mock, patch

from lazythumbs.views import LazyThumbRenderer, action

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
        self.size = (1000, 1000)
    def resize(self, size, _):
        self.called.append('resize')
        self.size = size
        return self
    def crop(self, dimensions):
        self.called.append('crop')
        return self


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

    def test_thumbnail_noop(self):
        """
        Test that no image operations occur if the desired w/h match image's
        existing w/h
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_img.size = (100, 100)
        img = renderer.thumbnail(width=100, img=mock_img)
        self.assertEqual(img.size[0], 100)
        self.assertEqual(img.size[1], 100)
        self.assertEqual(len(mock_img.called), 0)

    def test_thumbnail_square(self):
        """
        Test behavior of thumbnail action when no width == height
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_img.size = (100, 100)
        img = renderer.thumbnail(width=50, img=mock_img)
        self.assertEqual(img.size[0], 50)
        self.assertEqual(img.size[1], 50)
        self.assertEqual(len(mock_img.called), 1)
        self.assertTrue('resize' in mock_img.called)

    def test_thumbnail_no_upscaling(self):
        """
        Ensure that upscaling is forbidden in thumbnail action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        mock_img.size = (100, 100)
        img = renderer.thumbnail(width=20000, img=mock_img)

        self.assertEqual(img.size[0], 100)
        self.assertEqual(img.size[1], 100)
        self.assertEqual(len(mock_img.called), 0)

    def test_resize(self):
        """
        Test behavior of resize action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        img = renderer.resize(width=48, height=50, img=mock_img)
        self.assertEqual(img.size[1], 50)
        self.assertEqual(len(mock_img.called), 2)
        self.assertTrue('crop' in mock_img.called)
        self.assertTrue('resize' in mock_img.called)

    def test_resize_no_upscaling(self):
        """
        Ensure upscaling is forbidden in resize action.
        """
        renderer = LazyThumbRenderer()
        mock_img = MockImg()
        img = renderer.resize(width=2000, height=2000, img=mock_img)

        self.assertEqual(img.size[0], 1000)
        self.assertEqual(img.size[1], 1000)
        self.assertEqual(len(mock_img.called), 0)

class GetViewTest(TestCase):
    """ Test behavior of LazyThumbRenderer.get """

    def mc_factory(self, was_404):
        """
        churn out mocked caches with a preset .get(). Also a rapper?
        """
        mc = Mock()
        ret = was_404
        mc.get = Mock(return_value=ret)
        mc.set = Mock()
        return mc

    def setUp(self):
        self.renderer = LazyThumbRenderer()
        self.mock_Image = Mock()
        self.mock_img = Mock()
        self.mock_Image.open = Mock(return_value=self.mock_img)
        self.mock_img.size = [1,1]

    def test_img_404_warm_cache(self):
        """
        Ensure we go straight to a 404 response without setting anything new in
        cache or touching filesystem if we encounter a cached 404.
        """
        req = Mock()
        req.path = "/lt_cache/thumbnail/48/i/p.jpg"
        self.renderer._render_and_save = Mock()
        with patch('lazythumbs.views.cache', self.mc_factory(1)) as mc:
            resp = self.renderer.get(req, 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertFalse(mc.set.called)

    def test_img_404_cold_cache(self):
        """
        Basic 404: requested image is not found. Make sure proper response
        headers are set and the 404 was cached.
        """
        req = Mock()
        req.path = "/lt_cache/thumbnail/48/i/p.jpg"
        with patch('lazythumbs.views.cache', MockCache()) as mc:
            resp = self.renderer.get(req, 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertEqual(len(mc.cache.keys()), 1)
        key = mc.cache.keys()[0]
        cached = mc.cache[key]
        self.assertEqual(cached, 1)

    def test_img_200_cold_cache(self):
        """
        Pretend we found the requested rendered image on the filesystem. Ensure
        proper response headers are set and the rendered path was cached.
        """
        req = Mock()
        req.path = "/lt_cache/thumbnail/48/i/p.jpg"
        self.renderer.fs.save = Mock()
        with patch('lazythumbs.views.Image', self.mock_Image):
            with patch('lazythumbs.views.cache', MockCache()) as mc:
                resp = self.renderer.get(req, 'thumbnail', '48', 'i/p')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'image/jpeg')
        self.assertTrue('Cache-Control' in resp)
        self.assertEqual(resp.content, '') # empty buffer means raw_data is ''
        self.assertEqual(len(mc.cache.keys()), 1)

        key = mc.cache.keys()[0]
        cached = mc.cache[key]
        self.assertEqual(cached, False)

