import unittest

from text import is_palindrome


class HiddenPalindrome(unittest.TestCase):
    def test_quotes(self):
        self.assertTrue(is_palindrome("No 'x' in Nixon"))

    def test_empty(self):
        self.assertTrue(is_palindrome(""))

    def test_two_chars(self):
        self.assertFalse(is_palindrome("ab"))

    def test_apostrophe(self):
        self.assertTrue(is_palindrome("Madam, I'm Adam"))

    def test_digits(self):
        self.assertTrue(is_palindrome("12 3 21"))
        self.assertFalse(is_palindrome("12 3 4"))
