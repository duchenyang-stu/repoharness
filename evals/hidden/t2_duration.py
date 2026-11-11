import unittest

from timeparse import parse_duration


class HiddenDuration(unittest.TestCase):
    def test_all_units(self):
        self.assertEqual(parse_duration("1h1m1s"), 3661)

    def test_minutes_only(self):
        self.assertEqual(parse_duration("45m"), 2700)

    def test_zero(self):
        self.assertEqual(parse_duration("0s"), 0)

    def test_hours(self):
        self.assertEqual(parse_duration("10h"), 36000)
