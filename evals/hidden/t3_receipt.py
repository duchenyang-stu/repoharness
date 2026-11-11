import unittest

from cart import total_cents
from money import format_cents
from receipt import receipt


class HiddenReceipt(unittest.TestCase):
    def test_small_amounts_are_zero_padded(self):
        self.assertEqual(format_cents(5), "$0.05")
        self.assertEqual(format_cents(0), "$0.00")
        self.assertEqual(format_cents(1999), "$19.99")

    def test_total_uses_quantity(self):
        items = [{"name": "A", "price_cents": 100, "qty": 3}, {"name": "B", "price_cents": 50, "qty": 2}]
        self.assertEqual(total_cents(items), 400)

    def test_empty_receipt(self):
        self.assertEqual(receipt([]), "Total: $0.00")
