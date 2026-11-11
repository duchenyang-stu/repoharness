import unittest

from mathutil import clamp


class HiddenClamp(unittest.TestCase):
    def test_float(self):
        self.assertEqual(clamp(2.5, 1, 2), 2)

    def test_negative_range(self):
        self.assertEqual(clamp(-5, -3, -1), -3)
        self.assertEqual(clamp(-2, -3, -1), -2)

    def test_degenerate(self):
        self.assertEqual(clamp(0, 0, 0), 0)
        self.assertEqual(clamp(9, 4, 4), 4)
