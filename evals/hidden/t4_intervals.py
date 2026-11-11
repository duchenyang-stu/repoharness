import unittest

from intervals import merge_intervals


class HiddenIntervals(unittest.TestCase):
    def test_contained_interval(self):
        self.assertEqual(merge_intervals([(1, 4), (2, 3)]), [(1, 4)])

    def test_same_start_longer_later(self):
        self.assertEqual(merge_intervals([(1, 4), (0, 4)]), [(0, 4)])

    def test_nested_chain(self):
        self.assertEqual(merge_intervals([(1, 10), (2, 3), (4, 5)]), [(1, 10)])

    def test_single(self):
        self.assertEqual(merge_intervals([(1, 2)]), [(1, 2)])

    def test_input_not_mutated(self):
        data = [(5, 7), (1, 3)]
        merge_intervals(data)
        self.assertEqual(data, [(5, 7), (1, 3)])
