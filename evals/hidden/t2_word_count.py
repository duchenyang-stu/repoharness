import unittest

from text import word_count


class HiddenWordCount(unittest.TestCase):
    def test_whitespace_variants(self):
        self.assertEqual(word_count("a b  A\nb,b"), {"a": 2, "b": 3})

    def test_digits(self):
        self.assertEqual(word_count("x1 X1 x2"), {"x1": 2, "x2": 1})

    def test_only_punctuation(self):
        self.assertEqual(word_count("-- !!"), {})
