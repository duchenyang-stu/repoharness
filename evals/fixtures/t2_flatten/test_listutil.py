import unittest

from listutil import flatten


class FlattenTests(unittest.TestCase):
    def test_deep(self):
        self.assertEqual(flatten([1, [2, [3, [4]]]]), [1, 2, 3, 4])

    def test_empty(self):
        self.assertEqual(flatten([]), [])

    def test_flat(self):
        self.assertEqual(flatten([1, 2]), [1, 2])
