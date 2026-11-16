import unittest

from shop import Cart
from shop.tax import line_tax


class HiddenShop(unittest.TestCase):
    def test_half_up_not_bankers(self):
        self.assertEqual(line_tax(5, 0.1), 1)       # 0.5 -> 1
        self.assertEqual(line_tax(25, 0.1), 3)      # 2.5 -> 3
        self.assertEqual(line_tax(1050, 0.05), 53)  # 52.5 -> 53

    def test_decimal_accuracy(self):
        self.assertEqual(line_tax(1005, 0.07), 70)  # 70.35 -> 70
        self.assertEqual(line_tax(15, 0.07), 1)     # 1.05 -> 1

    def test_tax_is_per_line(self):
        cart = Cart(tax_rate=0.1)
        for name in "abc":
            cart.add(name, 105)                     # each 10.5 -> 11
        self.assertEqual(cart.tax(), 33)
        self.assertEqual(cart.total(), 315 + 33 + 599)

    def test_per_line_with_quantity(self):
        cart = Cart(tax_rate=0.05)
        cart.add("x", 30, 3)                        # line 90 -> 4.5 -> 5
        cart.add("y", 10, 1)                        # line 10 -> 0.5 -> 1
        self.assertEqual(cart.tax(), 6)

    def test_free_shipping_uses_pre_tax_subtotal(self):
        cart = Cart(tax_rate=0.1)
        cart.add("big", 4999)
        self.assertEqual(cart.total(), 4999 + 500 + 599)


if __name__ == "__main__":
    unittest.main()
