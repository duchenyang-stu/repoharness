import unittest

from importer import read_orders
from importer.models import Order


class ImporterTests(unittest.TestCase):
    def test_basic(self):
        text = "id,customer,amount\n1,alice,10.50\n2,bob,3\n"
        self.assertEqual(
            read_orders(text),
            [Order("1", "alice", 1050), Order("2", "bob", 300)],
        )

    def test_empty(self):
        self.assertEqual(read_orders(""), [])


if __name__ == "__main__":
    unittest.main()
