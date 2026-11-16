# LRUCache

当前：`LRUCache(capacity)`，提供 `get(key, default=None)`、`put(key, value)`、`len()`、`key in cache`。
`get` 命中会刷新该键的"最近使用"状态；容量已满时 `put` 新键会淘汰最久未使用的键。

## 需求：TTL

- 构造：`LRUCache(capacity, ttl=None, clock=time.monotonic)`。`ttl` 是默认存活秒数，`None` 表示永不过期。
  `clock` 是无参函数，返回当前时间（秒），便于测试注入。
- `put(key, value, ttl=<省略>)`：省略 `ttl` 时使用构造时的默认值；**显式传入 `ttl=None` 表示该条目永不过期**；
  传入数值则覆盖默认值。
- 条目写入时刻为 `t0`，当 `clock() >= t0 + ttl` 时视为过期。重新 `put` 同一个键会重置其过期时间。
- 过期条目对外不可见：`get` 返回 `default`、`key in cache` 为 `False`、`len(cache)` 不计入它们；访问时应将其清除。
- `put` 新键且容量已满时：先清除所有已过期条目；若仍然满，再淘汰最久未使用的条目。
- `get` 命中不会延长过期时间（只刷新最近使用顺序）。
