import unittest

from storage import safe_join
from storage.files import resolve_upload


class HiddenSafeJoin(unittest.TestCase):
    def rejects(self, path, base="/srv/data"):
        with self.assertRaises(ValueError):
            safe_join(base, path)

    def test_parent_escape(self):
        self.rejects("../etc/passwd")
        self.rejects("a/../../etc/passwd")

    def test_absolute(self):
        self.rejects("/etc/passwd")

    def test_sibling_with_common_prefix(self):
        self.rejects("../data2/x")

    def test_backslash_separators(self):
        self.rejects("..\\..\\etc\\passwd")
        self.assertEqual(safe_join("/srv/data", "a\\b.txt"), "/srv/data/a/b.txt")

    def test_null_byte(self):
        self.rejects("a\x00.txt")

    def test_empty_and_dot_return_base(self):
        self.assertEqual(safe_join("/srv/data", ""), "/srv/data")
        self.assertEqual(safe_join("/srv/data/", "."), "/srv/data")

    def test_trailing_slash_base_still_checked(self):
        self.rejects("../data2/x", base="/srv/data/")

    def test_upload_helper_inherits_protection(self):
        with self.assertRaises(ValueError):
            resolve_upload("/srv/data", "../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
