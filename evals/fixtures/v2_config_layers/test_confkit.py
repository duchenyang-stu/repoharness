import unittest

from confkit import load_config

SCHEMA = {"port": int, "debug": bool, "name": str}


class ConfkitTests(unittest.TestCase):
    def test_defaults(self):
        cfg = load_config(SCHEMA, {"port": 80, "debug": False, "name": "x"}, {}, {})
        self.assertEqual(cfg, {"port": 80, "debug": False, "name": "x"})

    def test_file_overrides_defaults(self):
        cfg = load_config(SCHEMA, {"port": 80, "debug": False, "name": "x"}, {"port": 8080}, {})
        self.assertEqual(cfg["port"], 8080)

    def test_string_in_file_is_parsed(self):
        cfg = load_config(SCHEMA, {"port": 80, "debug": False, "name": "x"}, {"port": "9000"}, {})
        self.assertEqual(cfg["port"], 9000)


if __name__ == "__main__":
    unittest.main()
