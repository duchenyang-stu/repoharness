import unittest

from timeparse import parse_duration


class ParseDurationTests(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(parse_duration("90s"), 90)

    def test_minutes(self):
        self.assertEqual(parse_duration("2m"), 120)

    def test_combined(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
