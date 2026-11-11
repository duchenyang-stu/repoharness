import unittest

import settings
from settings import build_settings


class SettingsTests(unittest.TestCase):
    def test_nested_override_keeps_siblings(self):
        result = build_settings({"db": {"port": 6543}})
        self.assertEqual(result["db"]["port"], 6543)
        self.assertEqual(result["db"]["host"], "localhost")

    def test_deeper_override(self):
        result = build_settings({"db": {"options": {"timeout": 5}}})
        self.assertEqual(result["db"]["options"], {"timeout": 5, "ssl": False})

    def test_defaults_not_mutated(self):
        build_settings({"debug": True, "db": {"port": 1}})
        self.assertFalse(settings.DEFAULTS["debug"])
        self.assertEqual(settings.DEFAULTS["db"]["port"], 5432)
