import unittest

from listutil import flatten


class HiddenFlatten(unittest.TestCase):
    def test_empty_nested(self):
        self.assertEqual(flatten([[[]], [1, [[2]]]]), [1, 2])

    def test_strings_not_split(self):
        self.assertEqual(flatten(["ab", ["cd"]]), ["ab", "cd"])

    def test_only_empty_lists(self):
        self.assertEqual(flatten([[], [[], []]]), [])
