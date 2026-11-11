from cache import LRUCache


class UserStore:
    def __init__(self, loader, capacity=2):
        self._loader = loader
        self._cache = LRUCache(capacity)
        self.loads = 0

    def get_user(self, user_id):
        user = self._cache.get(user_id)
        if user is None:
            self.loads += 1
            user = self._loader(user_id)
            self._cache.put(user_id, user)
        return user
