import errno
import os
import shutil
import tempfile
from unittest import TestCase

from mock import Mock, patch

from lazythumbs.views import LazyThumbRenderer, action
from lazythumbs.urls import urlpatterns
from django.core.urlresolvers import reverse, resolve


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
        self.mode = "RGB"

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

    def test_no_img_should_404(self):
        """
        When save fails with EEXIST error, it will try to read the file again
        But if it still can't be read, make sure it returns a 404 instead of 0-byte image.
        """
        req = Mock()
        req.path = "/lt_cache/thumbnail/48/i/p.jpg"
        self.renderer.fs.save = Mock()
        err = OSError()
        err.errno = errno.EEXIST
        self.renderer.fs.save.side_effect = err
        with patch('lazythumbs.views.Image', self.mock_Image):
            with patch('lazythumbs.views.cache', MockCache()):
                resp = self.renderer.get(req, 'thumbnail', '48', 'i/p')
        self.assertEqual(resp.status_code, 404)

class TestOddFiles(TestCase):

    # Disabled for now because PIL on Hudson doesn't have JPEG support
    def disabled_test_extensionless_gif(self):
        """If the image file is a GIF without an extension, we can produce
        a valid thumbnail for it."""

        # Note: this test image file was breaking thumbnails if lazythumbs didn't
        # see the .gif extension.  I tried creating a gif on the fly using
        # PIL but didn't hit the same problem, so it might be something about
        # this image that's special, maybe that it has a transparent background.
        # (The error was "cannot write mode P as JPEG"; the symptom was a 404
        # response.)

        MEDIA_ROOT = tempfile.gettempdir()

        # Need to override MEDIA_ROOT in both django file storage and lazythumbs views
        # and Django doesn't provide override_settings until 1.4
        with patch('django.core.files.storage.settings') as settings1:
            settings1.MEDIA_ROOT = MEDIA_ROOT

            with patch('lazythumbs.views.settings') as settings2:
                settings2.MEDIA_ROOT = MEDIA_ROOT

                testfile = os.path.join(os.path.dirname(__file__), "testdata", "testimage.gif")
                filename = None
                try:
                    filename = os.path.join(MEDIA_ROOT, "gif_without_extension")
                    shutil.copy(testfile, filename)
                    # Now we have a gif file in a filename that doesn't end in .gif

                    renderer = LazyThumbRenderer()
                    source_path = os.path.relpath(filename, MEDIA_ROOT)
                    rsp = renderer.get(
                        request=Mock(path="/thumbnail/x50/" + source_path),
                        action="thumbnail",
                        geometry="x50",
                        source_path=source_path
                        )
                    self.assertEqual(200, rsp.status_code)
                finally:
                    if filename:
                        os.remove(filename)


def test_paths(routes_to_test=()):
    for route in routes_to_test:
        path = route["url_path"]
        pattern = route["pattern_name"]

        # if kwparams:
        #     yield reverse(pattern, kwargs=kwparams), path
        # else:
        #     yield reverse(pattern), path

        yield resolve(path).url_name, pattern


class TestUrlMatching(TestCase):
    """
    Test that urls that are built by the template tag are properly matched by
    the lazythumbs.urls.urlpatterns
    """

    def setUp(self):
        self.routes_to_test = (
            dict(url_path='/lt/lt_cache/resize/5/p/i.jpg', pattern_name='lt_slash_sep'),
            dict(url_path='/lt/lt_cache/resize/5/5/p/i.jpg', pattern_name='lt_slash_sep'),
            dict(url_path='/lt/lt_cache/resize/5x5/p/i.jpg', pattern_name='lt_x_sep'),
            dict(url_path='/lt/lt_cache/resize/x/5/p/i.jpg', pattern_name='lt_x_width')
        )

    @patch('django.conf.settings')
    def test_url_matching(self, settings):
        settings.ROOT_URLCONF = urlpatterns
        routes_tested = 0
        for path1, path2 in test_paths(self.routes_to_test):
            routes_tested += 1
            self.assertEqual(path1, path2)
        self.assertEqual(routes_tested, 4)
