import unittest

from cachelib import LRUCache


class LRUTests(unittest.TestCase):
    def test_basic(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(len(cache), 2)

    def test_evicts_least_recently_used(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertNotIn("b", cache)
        self.assertIn("a", cache)

    def test_default(self):
        self.assertEqual(LRUCache(1).get("x", "d"), "d")


if __name__ == "__main__":
    unittest.main()
