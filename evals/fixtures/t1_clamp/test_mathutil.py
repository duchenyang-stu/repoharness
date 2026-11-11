import unittest

from mathutil import clamp


class ClampTests(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below(self):
        self.assertEqual(clamp(-1, 0, 10), 0)

    def test_above(self):
        self.assertEqual(clamp(11, 0, 10), 10)
