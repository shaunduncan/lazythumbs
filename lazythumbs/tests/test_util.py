from unittest import TestCase
from mock import patch

from lazythumbs.util import geometry_parse, build_geometry, get_img_attrs


class TestGeometry(TestCase):
    class TestException:
        pass

    def test_invalid_resize(self):
        self.assertRaises(self.TestException, geometry_parse, "resize", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "resize", "45x34x", self.TestException)

    def test_valid_resize(self):
        h, w = geometry_parse('resize', '10x20', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, 20)

    def test_invalid_thumb(self):
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "30x", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "x10x", self.TestException)

    def test_valid_thumb(self):
        h, w = geometry_parse('thumbnail', '10', self.TestException)
        self.assertEqual(h, 10)
        self.assertEqual(w, None)
        h, w = geometry_parse('thumbnail', 'x20', self.TestException)
        self.assertEqual(h, None)
        self.assertEqual(w, 20)

    def test_invalid_scale(self):
        self.assertRaises(self.TestException, geometry_parse, "scale", "boom", self.TestException)

    def test_build_geo(self):
        self.assertEqual(build_geometry(10, 20), "10x20")
        self.assertEqual(build_geometry(10, None), "10")
        self.assertEqual(build_geometry(None, 20), "x20")

class TestGetImgAttrs(TestCase):
    @patch('lazythumbs.util.compute_img')
    def test_no_height(self, mock_ci):
        get_img_attrs('url', 'noaction', 10)
        self.assertEqual(mock_ci.call_args[0][2], '10')

    @patch('lazythumbs.util.compute_img')
    def test_no_width(self, mock_ci):
        get_img_attrs('url', 'noaction', height=10)
        self.assertEqual(mock_ci.call_args[0][2], 'x10')

    @patch('lazythumbs.util.compute_img')
    def test_both_dimensions(self, mock_ci):
        get_img_attrs('url', 'noaction', 10, 20)
        self.assertEqual(mock_ci.call_args[0][2], '10x20')
