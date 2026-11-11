import unittest

from text import word_count


class WordCountTests(unittest.TestCase):
    def test_case_and_punctuation(self):
        self.assertEqual(word_count("Hello, hello world!"), {"hello": 2, "world": 1})

    def test_empty(self):
        self.assertEqual(word_count(""), {})
