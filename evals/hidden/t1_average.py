import unittest

from stats import average


class HiddenAverage(unittest.TestCase):
    def test_floats(self):
        self.assertEqual(average([1.5, 2.5]), 2.0)

    def test_negative(self):
        self.assertEqual(average([-1, 1]), 0)

    def test_repeated(self):
        self.assertEqual(average([7, 7, 7, 7]), 7)

    def test_empty_still_raises(self):
        with self.assertRaises(ValueError):
            average([])
