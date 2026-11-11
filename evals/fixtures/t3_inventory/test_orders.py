import unittest

from errors import InsufficientStock
from inventory import Inventory
from orders import place_order


class OrderTests(unittest.TestCase):
    def test_success(self):
        inv = Inventory({"a": 5, "b": 1})
        place_order(inv, [("a", 2), ("b", 1)])
        self.assertEqual(inv.available("a"), 3)
        self.assertEqual(inv.available("b"), 0)

    def test_raises_with_details(self):
        inv = Inventory({"a": 5, "b": 1})
        with self.assertRaises(InsufficientStock) as ctx:
            place_order(inv, [("a", 2), ("b", 3)])
        error = ctx.exception
        self.assertEqual((error.sku, error.requested, error.available), ("b", 3, 1))

    def test_failed_order_leaves_stock_unchanged(self):
        inv = Inventory({"a": 5, "b": 1})
        with self.assertRaises(InsufficientStock):
            place_order(inv, [("a", 2), ("b", 3)])
        self.assertEqual(inv.available("a"), 5)
        self.assertEqual(inv.available("b"), 1)
