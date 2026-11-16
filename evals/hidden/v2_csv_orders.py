import unittest

from importer import read_orders
from importer.errors import DuplicateIdError, MissingColumnError
from importer.models import Order


class HiddenImporter(unittest.TestCase):
    def test_quoted_comma(self):
        text = 'id,customer,amount\n1,"Smith, John",5.00\n'
        self.assertEqual(read_orders(text), [Order("1", "Smith, John", 500)])

    def test_header_case_order_and_spaces(self):
        text = " AMOUNT , ID ,Customer\n7.25,9,zed\n"
        self.assertEqual(read_orders(text), [Order("9", "zed", 725)])

    def test_blank_lines_ignored(self):
        text = "\nid,customer,amount\n\n1,a,1.00\n   \n2,b,2.00\n\n"
        self.assertEqual([o.id for o in read_orders(text)], ["1", "2"])

    def test_exact_decimal_amounts(self):
        text = "id,customer,amount\n1,a,19.99\n2,b,0.1\n3,c,1.15\n"
        self.assertEqual([o.amount_cents for o in read_orders(text)], [1999, 10, 115])

    def test_too_many_decimals(self):
        with self.assertRaises(ValueError):
            read_orders("id,customer,amount\n1,a,1.234\n")

    def test_duplicate_id_reports_line(self):
        text = "id,customer,amount\n1,a,1.00\n2,b,2.00\n1,c,3.00\n"
        with self.assertRaises(DuplicateIdError) as ctx:
            read_orders(text)
        self.assertEqual(ctx.exception.line, 4)
        self.assertEqual(ctx.exception.order_id, "1")

    def test_duplicate_line_counts_blank_lines(self):
        text = "id,customer,amount\n1,a,1.00\n\n1,c,3.00\n"
        with self.assertRaises(DuplicateIdError) as ctx:
            read_orders(text)
        self.assertEqual(ctx.exception.line, 4)

    def test_missing_column(self):
        with self.assertRaises(MissingColumnError) as ctx:
            read_orders("id,customer\n1,a\n")
        self.assertEqual(ctx.exception.column, "amount")


if __name__ == "__main__":
    unittest.main()
