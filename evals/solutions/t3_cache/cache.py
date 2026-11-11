from collections import OrderedDict


class LRUCache:
    """容量固定的 LRU 缓存：超出容量时淘汰最久未使用的键。get 和 put 都算一次使用。"""

    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
