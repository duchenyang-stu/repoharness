import unittest
from datetime import date

from dates import week_start, weeks_between


class WeekTests(unittest.TestCase):
    def test_midweek(self):
        self.assertEqual(week_start(date(2024, 5, 15)), date(2024, 5, 13))

    def test_monday_is_its_own_start(self):
        self.assertEqual(week_start(date(2024, 5, 13)), date(2024, 5, 13))

    def test_sunday_belongs_to_previous_monday(self):
        self.assertEqual(week_start(date(2024, 5, 19)), date(2024, 5, 13))

    def test_sunday_to_monday_is_one_week(self):
        self.assertEqual(weeks_between(date(2024, 5, 12), date(2024, 5, 13)), 1)

    def test_monday_to_sunday_is_same_week(self):
        self.assertEqual(weeks_between(date(2024, 5, 13), date(2024, 5, 19)), 0)
