import unittest

from errors import InsufficientStock, InventoryError
from inventory import Inventory
from orders import place_order


class HiddenInventory(unittest.TestCase):
    def test_unknown_sku(self):
        inv = Inventory({})
        with self.assertRaises(InsufficientStock) as ctx:
            place_order(inv, [("zzz", 1)])
        self.assertEqual(ctx.exception.available, 0)

    def test_repeated_sku_lines_are_cumulative(self):
        inv = Inventory({"a": 5})
        with self.assertRaises(InsufficientStock):
            place_order(inv, [("a", 3), ("a", 3)])
        self.assertEqual(inv.available("a"), 5)

    def test_exact_stock_is_allowed(self):
        inv = Inventory({"a": 2})
        place_order(inv, [("a", 2)])
        self.assertEqual(inv.available("a"), 0)

    def test_is_inventory_error(self):
        self.assertTrue(issubclass(InsufficientStock, InventoryError))

    def test_direct_remove_cannot_go_negative(self):
        inv = Inventory({"a": 1})
        with self.assertRaises(InsufficientStock):
            inv.remove("a", 2)
        self.assertEqual(inv.available("a"), 1)
