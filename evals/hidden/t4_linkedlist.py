import unittest

from linkedlist import LinkedList


def make(*values):
    ll = LinkedList()
    for value in values:
        ll.append(value)
    return ll


class HiddenLinkedList(unittest.TestCase):
    def test_reverse_empty_and_single(self):
        empty = make()
        empty.reverse()
        self.assertEqual(list(empty), [])
        single = make(1)
        single.reverse()
        self.assertEqual(list(single), [1])

    def test_append_after_reverse_goes_to_end(self):
        ll = make(1, 2, 3)
        ll.reverse()
        ll.append(0)
        self.assertEqual(list(ll), [3, 2, 1, 0])

    def test_remove_head(self):
        ll = make(1, 2, 3)
        self.assertTrue(ll.remove(1))
        self.assertEqual(list(ll), [2, 3])

    def test_remove_tail_then_append(self):
        ll = make(1, 2, 3)
        self.assertTrue(ll.remove(3))
        ll.append(4)
        self.assertEqual(list(ll), [1, 2, 4])
        self.assertEqual(len(ll), 3)

    def test_remove_only_element_then_append(self):
        ll = make(1)
        self.assertTrue(ll.remove(1))
        self.assertEqual(len(ll), 0)
        ll.append(2)
        self.assertEqual(list(ll), [2])

    def test_remove_first_occurrence_only(self):
        ll = make(1, 2, 1)
        ll.remove(1)
        self.assertEqual(list(ll), [2, 1])
