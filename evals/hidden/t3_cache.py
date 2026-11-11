import unittest

from cache import LRUCache


class HiddenCache(unittest.TestCase):
    def test_put_existing_key_refreshes_recency(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 10)

    def test_capacity_one(self):
        cache = LRUCache(1)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)

    def test_default_for_missing(self):
        self.assertEqual(LRUCache(2).get("x", "d"), "d")

    def test_eviction_order_after_gets(self):
        cache = LRUCache(3)
        for key in "abc":
            cache.put(key, key)
        cache.get("a")
        cache.get("b")
        cache.put("d", "d")
        self.assertIsNone(cache.get("c"))
