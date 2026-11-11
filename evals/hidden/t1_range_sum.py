import unittest

from sumutil import range_sum


class HiddenRangeSum(unittest.TestCase):
    def test_hundred(self):
        self.assertEqual(range_sum(100), 5050)

    def test_ten(self):
        self.assertEqual(range_sum(10), 55)

    def test_negative(self):
        self.assertEqual(range_sum(-3), 0)
