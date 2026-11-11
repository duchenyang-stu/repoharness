import unittest
from datetime import date

from dates import week_start, weeks_between


class HiddenWeeks(unittest.TestCase):
    def test_year_boundary_start(self):
        self.assertEqual(week_start(date(2025, 1, 1)), date(2024, 12, 30))

    def test_year_boundary_same_week(self):
        self.assertEqual(weeks_between(date(2024, 12, 30), date(2025, 1, 5)), 0)

    def test_two_weeks(self):
        self.assertEqual(weeks_between(date(2024, 12, 29), date(2025, 1, 6)), 2)

    def test_same_day(self):
        self.assertEqual(weeks_between(date(2024, 5, 15), date(2024, 5, 15)), 0)
