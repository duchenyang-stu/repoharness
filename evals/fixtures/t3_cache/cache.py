from collections import OrderedDict


class LRUCache:
    """容量固定的 LRU 缓存：超出容量时淘汰最久未使用的键。get 和 put 都算一次使用。"""

    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def put(self, key, value):
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
