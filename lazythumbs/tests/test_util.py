from unittest import TestCase
from mock import patch, Mock


from django.conf import settings
from lazythumbs.util import geometry_parse, build_geometry, compute_img, get_img_attrs, get_source_img_attrs
from lazythumbs.util import get_format, get_attr_string, get_placeholder_url, _construct_lt_img_url

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
        """ test that thumbnail with 2d or width/height only works """
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

    def test_build_geo_resize(self):
        """ test that build_geometry builds the correct geometry with 2d and width/height only """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        self.assertEqual(build_geometry('resize', 10, 20), "10/20")
        self.assertEqual(build_geometry('resize', 10, None), "10")
        self.assertEqual(build_geometry('resize', None, 20), "x/20")
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

    def test_build_geo_thumbnail(self):
        """ test that build_geometry builds the correct geometry with 2d and width/height only """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        self.assertEqual(build_geometry('thumbnail', 10, 20), "10")
        self.assertEqual(build_geometry('thumbnail', 10, None), "10")
        self.assertEqual(build_geometry('thumbnail', None, 20), "x/20")
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

    @patch('lazythumbs.util.settings')
    def test_build_geo_with_x_dim_resize(self, settings):
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = True
        """ test that build_geometry builds the correct geometry with 2d and width/height only """
        self.assertEqual(build_geometry('resize', 10, 20), "10x20")
        self.assertEqual(build_geometry('resize', 10, None), "10")
        self.assertEqual(build_geometry('resize', None, 20), "x20")

    @patch('lazythumbs.util.settings')
    def test_build_geo_with_x_dim_thumbnail(self, settings):
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = True
        """ test that build_geometry builds the correct geometry with 2d and width/height only """
        self.assertEqual(build_geometry('thumbnail', 10, 20), "10")
        self.assertEqual(build_geometry('thumbnail', 10, None), "10")
        self.assertEqual(build_geometry('thumbnail', None, 20), "x20")


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
        path = "http://www.notus.com/path/to/img.jpg"
        attrs = compute_img(path, "resize", "100x100")
        self.assertEqual(attrs['height'], '')
        self.assertEqual(attrs['width'], '')
        self.assertEqual(attrs['src'], path)

    def test_mapped_secondary_url(self):
        """ if someone tries to thumbnail an image for different known url, mapping should be done """
        path = "http://example.com/media/path/to/img.jpg"
        attrs = compute_img(path, "resize", "100x100")
        self.assertEqual(attrs['height'], '100')
        self.assertEqual(attrs['width'], '100')
        self.assertEqual(attrs['src'], 'http://example.com/media/lt/lt_cache/resize/100/100/path/to/img.jpg')

    def test_local_url(self):
        """ if thing is a url and it's local we can attempt to resize it """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        url = settings.MEDIA_URL + 'path/img.jpg'
        attrs = compute_img(url, "resize", "200x200")
        self.assertEqual(attrs['height'], '200')
        self.assertEqual(attrs['width'], '200')
        self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/resize/200/200/path/img.jpg')
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

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
            self.assertEqual(attrs['src'], settings.MEDIA_URL + 'path/img.jpg')
            self.assertEqual(attrs['width'], '10')
            self.assertEqual(attrs['height'], '20')

    def test_2d_resize(self):
        """ resize with two dimensions returns the proper path """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', '5x50')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/resize/5/50/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '50')
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

    def test_width_resize(self):
        """ resize with only width return the proper path and size """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', '5')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/resize/5/5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

    def test_height_resize(self):
        """ resize with only height returns the proper path and size """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'resize', 'x5')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/resize/5/5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = old_x_for_dim

    def test_thumb_both(self):
        """ thumbnail with both dimensions works """
        old_x_for_dim = getattr(settings, 'LAZYTHUMBS_USE_X_FOR_DIMENSIONS', None)
        settings.LAZYTHUMBS_USE_X_FOR_DIMENSIONS = False
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', '5x5')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/thumbnail/5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '5')

    def test_thumb_width(self):
        """ thumbnail with width only computes the proper height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', '5')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/thumbnail/5/path/img.jpg')
            self.assertEqual(attrs['width'], '5')
            self.assertEqual(attrs['height'], '10')

    def test_thumb_height(self):
        """ thumbnail with height only computes the proper height """
        with patch('lazythumbs.util.quack', self.get_fake_quack('path/img.jpg', width=100, height=200)):
            attrs = compute_img(Mock(), 'thumbnail', 'x10')
            self.assertEqual(attrs['src'], settings.LAZYTHUMBS_URL + 'lt_cache/thumbnail/5/path/img.jpg')
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


class TestGetFormat(TestCase):
    """ These tests actually rely on PIL """

    def test_notaformat(self):
        """ get_format will assume JPEG for unknown formats """
        self.assertEqual(get_format("path/img"), 'JPEG')

    def test_jpeg(self):
        self.assertEqual(get_format("path/img.jpeg"), 'JPEG')
        self.assertEqual(get_format("path/img.jpg"), 'JPEG')

    def test_gif(self):
        self.assertEqual(get_format("path/img.gif"), 'GIF')

    def test_png(self):
        self.assertEqual(get_format("path/img.png"), 'PNG')


class TestGetAttrString(TestCase):
    def test_both(self):
        """ make sure the attr string has both if both are given """
        attr_dict = dict(src="http://path.jpg", width="10", height="20")
        attr_str = get_attr_string(attr_dict)
        self.assertTrue('width="10"' in attr_str)
        self.assertTrue('height="20"' in attr_str)
        self.assertTrue('src="http://path.jpg"' in attr_str)

    def test_width(self):
        """ make sure the attr string has only width if that is all that is given """
        attr_dict = dict(src="http://path.jpg", width="10", height="")
        attr_str = get_attr_string(attr_dict)
        self.assertTrue('width="10"' in attr_str)
        self.assertFalse('height' in attr_str)
        self.assertTrue('src="http://path.jpg"' in attr_str)

    def test_height(self):
        """ make sure the attr string has only height if that is all that is given """
        attr_dict = dict(src="http://path.jpg", width="", height="23")
        attr_str = get_attr_string(attr_dict)
        self.assertTrue('height="23"' in attr_str)
        self.assertFalse('width' in attr_str)
        self.assertTrue('src="http://path.jpg"' in attr_str)

    def test_neither(self):
        """ make sure the empty string is returned if that is all that is given"""
        attr_dict = dict(src="http://path.jpg", width="", height="")
        attr_str = get_attr_string(attr_dict)
        self.assertFalse('width' in attr_str)
        self.assertFalse('height' in attr_str)
        self.assertTrue('src="http://path.jpg"' in attr_str)


class TestGetPlaceholderUrl(TestCase):

    def test_local_url(self):
        path = 'path/img.jpg'
        expected = _construct_lt_img_url (settings.LAZYTHUMBS_URL, '{{ action }}', '{{ dimensions }}', path)
        self.assertEqual(get_placeholder_url(path), expected)

    def test_foreign_url(self):
        path = 'http://path.com/img.jpg'
        self.assertEqual(get_placeholder_url(path), path)

    def test_mapped_secondary_url(self):
        path = "http://example.com/media/path/to/img.jpg"
        self.assertEqual(get_placeholder_url(path),
                         'http://example.com/media/lt/lt_cache/{{ action }}/{{ dimensions }}/path/to/img.jpg')


class TestGetSourceImgAttrs(TestCase):

    def test_valid_object(self):
        img = Mock()
        img.height = 100
        img.width = 50

        attrs = get_source_img_attrs(img)

        self.assertEqual(attrs['height'], 100)
        self.assertEqual(attrs['width'], 50)

    def test_invalid_object(self):

        img = 'foo'

        attrs = get_source_img_attrs(img)

        self.assertEqual(attrs['height'], None)
        self.assertEqual(attrs['width'], None)
