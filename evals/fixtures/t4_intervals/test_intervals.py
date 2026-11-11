import unittest

from intervals import merge_intervals


class MergeTests(unittest.TestCase):
    def test_overlapping(self):
        self.assertEqual(
            merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]),
            [(1, 6), (8, 10), (15, 18)],
        )

    def test_unsorted_and_touching(self):
        self.assertEqual(merge_intervals([(5, 7), (1, 3), (3, 4)]), [(1, 4), (5, 7)])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])
