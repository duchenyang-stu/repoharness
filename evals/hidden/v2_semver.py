import unittest

from semverlib import Version
from semverlib.ranges import satisfies


class HiddenSemver(unittest.TestCase):
    def test_spec_example_ordering(self):
        ordered = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
                   "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
        shuffled = [ordered[i] for i in (7, 3, 0, 5, 2, 6, 1, 4)]
        self.assertEqual([str(v) for v in sorted(Version(t) for t in shuffled)], ordered)

    def test_release_above_prerelease(self):
        self.assertTrue(Version("1.0.0-rc.1") < Version("1.0.0"))
        self.assertTrue(Version("1.0.0") > Version("1.0.0-rc.1"))

    def test_numeric_identifiers_compare_numerically(self):
        self.assertTrue(Version("1.0.0-beta.2") < Version("1.0.0-beta.11"))

    def test_numeric_below_alphanumeric(self):
        self.assertTrue(Version("1.0.0-1") < Version("1.0.0-alpha"))

    def test_fewer_fields_is_lower(self):
        self.assertTrue(Version("1.0.0-alpha") < Version("1.0.0-alpha.1"))

    def test_build_metadata_ignored(self):
        self.assertEqual(Version("1.0.0+a"), Version("1.0.0+b"))
        self.assertEqual(hash(Version("1.0.0+a")), hash(Version("1.0.0+b")))
        self.assertFalse(Version("1.0.0+a") < Version("1.0.0+b"))
        self.assertFalse(Version("1.0.0+a") > Version("1.0.0+b"))
        self.assertEqual(len({Version("1.0.0+a"), Version("1.0.0+b")}), 1)

    def test_full_comparison_operators(self):
        a, b = Version("1.0.0-rc.1"), Version("1.0.0")
        self.assertTrue(a <= b and b >= a and a != b and b > a)
        self.assertTrue(Version("1.0.0+x") <= Version("1.0.0") and Version("1.0.0+x") >= Version("1.0.0"))

    def test_invalid_versions(self):
        for text in ["1.0", "01.0.0", "1.0.0-", "1.0.0-a..b", "1.0.0-01", "a.b.c", ""]:
            with self.assertRaises(ValueError, msg=text):
                Version(text)

    def test_ranges_use_precedence(self):
        self.assertTrue(satisfies(Version("1.0.0"), ">=1.0.0-rc.1"))
        self.assertFalse(satisfies(Version("1.0.0-rc.1"), ">=1.0.0"))
        self.assertTrue(satisfies(Version("1.0.0+meta"), "==1.0.0"))


if __name__ == "__main__":
    unittest.main()
