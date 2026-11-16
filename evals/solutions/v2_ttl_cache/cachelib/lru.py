import time
from collections import OrderedDict

_UNSET = object()


class LRUCache:
    def __init__(self, capacity, ttl=None, clock=time.monotonic):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.ttl = ttl
        self._clock = clock
        self._data = OrderedDict()  # key -> (value, expires_at or None)

    def _expired(self, expires_at):
        return expires_at is not None and self._clock() >= expires_at

    def _purge(self):
        for key in [k for k, (_, exp) in self._data.items() if self._expired(exp)]:
            del self._data[key]

    def get(self, key, default=None):
        item = self._data.get(key)
        if item is None:
            return default
        value, expires_at = item
        if self._expired(expires_at):
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def put(self, key, value, ttl=_UNSET):
        effective = self.ttl if ttl is _UNSET else ttl
        expires_at = None if effective is None else self._clock() + effective
        if key in self._data:
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self.capacity:
                self._purge()
            if len(self._data) >= self.capacity:
                self._data.popitem(last=False)
        self._data[key] = (value, expires_at)

    def __len__(self):
        self._purge()
        return len(self._data)

    def __contains__(self, key):
        item = self._data.get(key)
        if item is None:
            return False
        if self._expired(item[1]):
            del self._data[key]
            return False
        return True
