import unittest

from confkit import ConfigError, load_config

SCHEMA = {"port": int, "debug": bool, "name": str, "ratio": float}
DEFAULTS = {"port": 80, "debug": False, "name": "x", "ratio": 0.5}


class HiddenConfig(unittest.TestCase):
    def test_env_beats_file(self):
        cfg = load_config(SCHEMA, DEFAULTS, {"port": 8080}, {"APP_PORT": "9090"})
        self.assertEqual(cfg["port"], 9090)

    def test_custom_prefix(self):
        cfg = load_config(SCHEMA, DEFAULTS, {}, {"SVC_NAME": "api", "APP_NAME": "wrong"}, prefix="SVC_")
        self.assertEqual(cfg["name"], "api")

    def test_bool_words(self):
        for text, expected in [("false", False), ("False", False), ("0", False), ("off", False), ("no", False),
                               ("", False), ("true", True), ("1", True), (" YES ", True), ("on", True)]:
            cfg = load_config(SCHEMA, DEFAULTS, {}, {"APP_DEBUG": text})
            self.assertIs(cfg["debug"], expected, text)

    def test_bool_in_file_as_string(self):
        cfg = load_config(SCHEMA, DEFAULTS, {"debug": "false"}, {})
        self.assertIs(cfg["debug"], False)

    def test_typed_file_values_pass_through(self):
        cfg = load_config(SCHEMA, DEFAULTS, {"debug": True, "port": 1234}, {})
        self.assertIs(cfg["debug"], True)
        self.assertEqual(cfg["port"], 1234)

    def test_invalid_bool(self):
        with self.assertRaises(ConfigError) as ctx:
            load_config(SCHEMA, DEFAULTS, {}, {"APP_DEBUG": "maybe"})
        self.assertEqual(ctx.exception.key, "debug")

    def test_invalid_int_does_not_fall_back(self):
        with self.assertRaises(ConfigError) as ctx:
            load_config(SCHEMA, DEFAULTS, {}, {"APP_PORT": "eighty"})
        self.assertEqual(ctx.exception.key, "port")

    def test_invalid_float(self):
        with self.assertRaises(ConfigError) as ctx:
            load_config(SCHEMA, DEFAULTS, {"ratio": "abc"}, {})
        self.assertEqual(ctx.exception.key, "ratio")

    def test_missing_key(self):
        with self.assertRaises(ConfigError) as ctx:
            load_config(SCHEMA, {"port": 1, "debug": False, "name": "x"}, {}, {})
        self.assertEqual(ctx.exception.key, "ratio")
        self.assertEqual(ctx.exception.message, "missing")

    def test_unknown_keys_ignored(self):
        cfg = load_config(SCHEMA, DEFAULTS, {"extra": 1}, {"APP_OTHER": "2"})
        self.assertNotIn("extra", cfg)
        self.assertNotIn("other", cfg)


if __name__ == "__main__":
    unittest.main()
