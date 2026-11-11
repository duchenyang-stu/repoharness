import unittest

from stats import average


class AverageTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(average([2, 4, 6]), 4)

    def test_single(self):
        self.assertEqual(average([10]), 10)

    def test_empty(self):
        with self.assertRaises(ValueError):
            average([])
