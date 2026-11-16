import unittest

from storage import safe_join
from storage.files import resolve_avatar, resolve_upload


class StorageTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(safe_join("/srv/data", "a/b.txt"), "/srv/data/a/b.txt")

    def test_inner_dotdot_ok(self):
        self.assertEqual(safe_join("/srv/data", "a/../b.txt"), "/srv/data/b.txt")

    def test_helpers(self):
        self.assertEqual(resolve_avatar("/srv/data", 7), "/srv/data/avatars/7.png")
        self.assertEqual(resolve_upload("/srv/data", "x.txt"), "/srv/data/uploads/x.txt")


if __name__ == "__main__":
    unittest.main()
