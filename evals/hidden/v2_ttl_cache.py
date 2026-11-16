import unittest

from cachelib import LRUCache


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class HiddenTTL(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def cache(self, capacity=3, ttl=10):
        return LRUCache(capacity, ttl=ttl, clock=self.clock)

    def test_expires_at_boundary(self):
        cache = self.cache()
        cache.put("a", 1)
        self.clock.now += 9
        self.assertEqual(cache.get("a"), 1)
        self.clock.now += 1
        self.assertIsNone(cache.get("a"))

    def test_expired_hidden_from_contains_and_len(self):
        cache = self.cache()
        cache.put("a", 1)
        cache.put("b", 2)
        self.clock.now += 11
        self.assertNotIn("a", cache)
        self.assertEqual(len(cache), 0)

    def test_put_resets_expiry(self):
        cache = self.cache()
        cache.put("a", 1)
        self.clock.now += 8
        cache.put("a", 2)
        self.clock.now += 8
        self.assertEqual(cache.get("a"), 2)

    def test_get_does_not_extend_expiry(self):
        cache = self.cache()
        cache.put("a", 1)
        self.clock.now += 6
        cache.get("a")
        self.clock.now += 5
        self.assertIsNone(cache.get("a"))

    def test_per_put_ttl_overrides(self):
        cache = self.cache(ttl=10)
        cache.put("short", 1, ttl=2)
        cache.put("long", 2, ttl=50)
        self.clock.now += 5
        self.assertIsNone(cache.get("short"))
        self.assertEqual(cache.get("long"), 2)

    def test_explicit_none_means_never_expire(self):
        cache = self.cache(ttl=10)
        cache.put("forever", 1, ttl=None)
        cache.put("normal", 2)
        self.clock.now += 1000
        self.assertEqual(cache.get("forever"), 1)
        self.assertIsNone(cache.get("normal"))

    def test_full_cache_purges_expired_before_evicting_lru(self):
        cache = self.cache(capacity=2, ttl=10)
        cache.put("old", 1, ttl=1)    # will expire
        cache.put("keep", 2)
        cache.get("old")              # 'old' is now most recently used, 'keep' is LRU
        self.clock.now += 2
        cache.put("new", 3)           # must drop expired 'old', NOT the live LRU 'keep'
        self.assertEqual(cache.get("keep"), 2)
        self.assertEqual(cache.get("new"), 3)

    def test_no_ttl_default_never_expires(self):
        cache = LRUCache(2, clock=self.clock)
        cache.put("a", 1)
        self.clock.now += 10**6
        self.assertEqual(cache.get("a"), 1)


if __name__ == "__main__":
    unittest.main()
