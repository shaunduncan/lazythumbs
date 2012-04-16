from unittest import TestCase
from mock import patch, Mock


from django.conf import settings
from lazythumbs.util import geometry_parse, build_geometry, compute_img, get_img_attrs


class TestGeometry(TestCase):
    class TestException:
        pass

    def test_invalid_resize(self):
        """ test that invalid geometry with resize raises the exception """
        self.assertRaises(self.TestException, geometry_parse, "resize", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "resize", "45x34x", self.TestException)

    def test_valid_resize(self):
        """ test that resize computes the correct geometry for 2d and width/height only """
        h, w = geometry_parse('resize', '10x20', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, 20)
        h, w = geometry_parse('resize', '10', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, 10)
        h, w = geometry_parse('resize', 'x10', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, 10)

    def test_invalid_thumb(self):
        """ test that thumbnail with invalid geometry raises the exception """
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "30x", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "x10x", self.TestException)

    def test_valid_thumb(self):
        """ test that thumbnail with 2d or wisth/heigh only works """
        h, w = geometry_parse('thumbnail', '10x20', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, 20)
        h, w = geometry_parse('thumbnail', '10', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, None)
        h, w = geometry_parse('thumbnail', 'x20', self.TestException)
        self.assertEqual(h, None)
        self.assertEqual(w, 20)

    def test_invalid_scale(self):
        """ test that scale will raise the exception with an invalid geometry """
        self.assertRaises(self.TestException, geometry_parse, "scale", "boom", self.TestException)

    def test_build_geo(self):
        """ test that build_geometry builds the correct geometry with 2d and width/height only """
        self.assertEqual(build_geometry(10, 20), "10x20")
        self.assertEqual(build_geometry(10, None), "10")
        self.assertEqual(build_geometry(None, 20), "x20")

class TestComputeIMG(TestCase):

    def get_fake_quack(self, url='', width=None, height=None):
        def fake_quack(thing, properties, levels=[], default=None):
            if 'width' in properties:
                return width
            if 'height' in properties:
                return height
            if 'url' in properties:
                return url
        return fake_quack

    def test_foreign_url(self):
        """ if someone tries to thumbnail an image not at MEDIA_ROOT return it unchanged """
        path = "http://www.example.com/path/to/img.jpg"
        attrs = compute_img(path, "resize", "100x100")
        self.assertEqual(attrs['height'], '')
        self.assertEqual(attrs['width'], '')
        self.assertEqual(attrs['src'], path)

    def test_local_url(self):
        """ if thing is a url and it's local we can attempt to resize it """
        url = settings.MEDIA_URL + 'path/img.jpg'
        attrs = compute_img(url, "resize", "200x200")
        self.assertEqual(attrs['height'], '200')
        self.assertEqual(attrs['width'], '200')
        self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/resize/200x200/path/img.jpg')

    def test_no_url(self):
        """ If there is no url all attrs shoudl be '' """
        with patch('lazythumbs.util.quack', self.get_fake_quack(width=10, height=20)):
            attrs = compute_img(Mock(), 'resize', '100x200')
            self.assertEqual(attrs['src'], '')
            self.assertEqual(attrs['width'], '')
            self.assertEqual(attrs['height'], '')

    def test_bad_geo(self):
        """ if the geometry won't parse we should return the original image and it's width/height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=10, height=20)):
            attrs = compute_img(Mock(), 'resize', 'XsxeX')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/path/img.jpg')
            self.assertEqual(attrs['width'], '10')
            self.assertEqual(attrs['height'], '20')

    def test_too_wide(self):
        """ if the size requested is too wide we should just return the original and it's width/height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=10, height=20)):
            attrs = compute_img(Mock(), 'resize', '100x5')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/path/img.jpg')
            self.assertEqual(attrs['width'], '10')
            self.assertEqual(attrs['height'], '20')

    def test_too_tall(self):
        """ if the size requested is too tall we should just return the original and it's width/height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=10, height=20)):
            attrs = compute_img(Mock(), 'resize', '5x50')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/path/img.jpg')
            self.assertEqual(attrs['width'], '10')
            self.assertEqual(attrs['height'], '20')

    def test_2d_resize(self):
        """ resize with two dimensions returns the proper path """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', '5x50')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/resize/5x50/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '50')

    def test_width_resize(self):
        """ resize with only width return the proper path and size """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', '5')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/resize/5x5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')

    def test_height_resize(self):
        """ resize with only height returns the proper path and size """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', 'x5')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/resize/5x5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')

    def test_thumb_both(self):
        """ thumbnail with both dimensions works """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', '5x5')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/thumbnail/5x5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')

    def test_thumb_width(self):
        """ thumbnail with width only computes the proper height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', '5')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/thumbnail/5x10/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '10')

    def test_thumb_height(self):
        """ thumbnail with height only computes the proper height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', 'x10')
            self.assertEqual(attrs['src'], 'http://media.example.com/media/lt/lt_cache/thumbnail/5x10/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '10')


class TestGetImgAttrs(TestCase):
    @patch('lazythumbs.util.compute_img')
    def test_no_height(self, mock_ci):
        """ get_img_attrs calls compute with the proper geometry when it's given no height """
        get_img_attrs('url', 'noaction', 10)
        self.assertEqual(mock_ci.call_args[0][2], '10')

    @patch('lazythumbs.util.compute_img')
    def test_no_width(self, mock_ci):
        """ get_img_attrs calls compute with the proper geometry when it's given no width """
        get_img_attrs('url', 'noaction', height=10)
        self.assertEqual(mock_ci.call_args[0][2], 'x10')

    @patch('lazythumbs.util.compute_img')
    def test_both_dimensions(self, mock_ci):
        """ get_img_attrs call compute with the proper geometry when it's given both dimensions """
        get_img_attrs('url', 'noaction', 10, 20)
        self.assertEqual(mock_ci.call_args[0][2], '10x20')
