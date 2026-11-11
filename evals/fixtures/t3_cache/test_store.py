import unittest

from cache import LRUCache
from store import UserStore


class CacheTests(unittest.TestCase):
    def test_get_refreshes_recency(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)


class StoreTests(unittest.TestCase):
    def test_recently_used_user_stays_cached(self):
        store = UserStore(lambda i: {"id": i}, capacity=2)
        for user_id in (1, 2, 1, 3, 1):
            store.get_user(user_id)
        self.assertEqual(store.loads, 3)
