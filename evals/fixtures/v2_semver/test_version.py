import unittest

from semverlib import Version


class VersionTests(unittest.TestCase):
    def test_numeric_not_lexicographic(self):
        self.assertTrue(Version("1.2.3") < Version("1.10.0"))
        self.assertTrue(Version("2.0.0") > Version("1.99.99"))

    def test_str_roundtrip(self):
        self.assertEqual(str(Version("1.2.3-rc.1+b5")), "1.2.3-rc.1+b5")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            Version("1.2")


if __name__ == "__main__":
    unittest.main()
