import unittest

from linkedlist import LinkedList


def make(*values):
    ll = LinkedList()
    for value in values:
        ll.append(value)
    return ll


class LinkedListTests(unittest.TestCase):
    def test_reverse(self):
        ll = make(1, 2, 3)
        ll.reverse()
        self.assertEqual(list(ll), [3, 2, 1])

    def test_remove_middle(self):
        ll = make(1, 2, 3)
        self.assertTrue(ll.remove(2))
        self.assertEqual(list(ll), [1, 3])
        self.assertEqual(len(ll), 2)

    def test_remove_missing(self):
        ll = make(1, 2)
        self.assertFalse(ll.remove(9))
        self.assertEqual(list(ll), [1, 2])
