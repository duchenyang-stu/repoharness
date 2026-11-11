import unittest

from receipt import receipt


class ReceiptTests(unittest.TestCase):
    def test_receipt(self):
        items = [
            {"name": "Widget", "price_cents": 250, "qty": 2},
            {"name": "Gadget", "price_cents": 1005, "qty": 1},
        ]
        expected = "Widget x2  $5.00\nGadget x1  $10.05\nTotal: $15.05"
        self.assertEqual(receipt(items), expected)
