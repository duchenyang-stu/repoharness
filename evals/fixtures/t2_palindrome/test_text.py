import unittest

from text import is_palindrome


class PalindromeTests(unittest.TestCase):
    def test_sentence(self):
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))

    def test_not_palindrome(self):
        self.assertFalse(is_palindrome("hello"))

    def test_question(self):
        self.assertTrue(is_palindrome("Was it a car or a cat I saw?"))
