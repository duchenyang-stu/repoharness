import unittest

from sumutil import range_sum


class RangeSumTests(unittest.TestCase):
    def test_four(self):
        self.assertEqual(range_sum(4), 10)

    def test_one(self):
        self.assertEqual(range_sum(1), 1)

    def test_zero(self):
        self.assertEqual(range_sum(0), 0)
