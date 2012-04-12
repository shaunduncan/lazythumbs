from unittest import TestCase
from mock import Mock

from lazythumbs.util import geometry_parse


class TestGeometry(TestCase):
    class TestException:
        def __init__(self, arg_str):
            pass

    def test_invalid_resize(self):
        self.assertRaises(self.TestException, geometry_parse, "resize", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "resize", "45x34x", self.TestException)

    def test_valid_resize(self):
        h, w = geometry_parse('resize', '10x20', self.TestException)
        self.assertEqual(h, '10')
        self.assertEqual(w, '20')

    def test_invalid_thumb(self):
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "boom", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "30x", self.TestException)
        self.assertRaises(self.TestException, geometry_parse, "thumbnail", "x10x", self.TestException)

    def test_valid_thumb(self):
        h, w = geometry_parse('thumbnail', '10', self.TestException)
        self.assertEqual(h, '10')
        self.assertEqual(w, None)
        h, w = geometry_parse('thumbnail', 'x20', self.TestException)
        self.assertEqual(h, None)
        self.assertEqual(w, '20')

    def test_invalid_scale(self):
        self.assertRaises(self.TestException, geometry_parse, "scale", "boom", self.TestException)
