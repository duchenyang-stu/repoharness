import unittest

from shop import Cart
from shop.shipping import shipping_cents
from shop.tax import line_tax


class CartTests(unittest.TestCase):
    def test_subtotal(self):
        cart = Cart()
        cart.add("pen", 250, 4)
        cart.add("ink", 1000)
        self.assertEqual(cart.subtotal(), 2000)

    def test_exact_tax(self):
        self.assertEqual(line_tax(1000, 0.1), 100)

    def test_total_with_exact_tax(self):
        cart = Cart(tax_rate=0.1)
        cart.add("a", 1000, 2)
        self.assertEqual(cart.total(), 2000 + 200 + 599)

    def test_shipping(self):
        self.assertEqual(shipping_cents(4999), 599)
        self.assertEqual(shipping_cents(5000), 0)

    def test_qty_validation(self):
        with self.assertRaises(ValueError):
            Cart().add("x", 1, 0)


if __name__ == "__main__":
    unittest.main()
