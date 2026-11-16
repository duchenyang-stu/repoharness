# retry

`@retry(max_attempts=3, base_delay=0.1, max_delay=2.0, exceptions=(Exception,))`

- 被装饰函数最多执行 `max_attempts` 次（含第一次）。
- 只有抛出 `exceptions` 中列出的异常才会重试；其它异常立即向外抛出，不再重试。
- 第 n 次失败后（n 从 1 开始）等待 `min(base_delay * 2 ** (n - 1), max_delay)` 秒再重试。
  即等待序列为 base, 2*base, 4*base ... 并以 max_delay 封顶。
- 最后一次尝试失败后**不再等待**，直接抛出该次异常。
- 等待通过模块级函数 `sleep(seconds)` 完成（测试会替换它）。
- 装饰后的函数应保留原函数的 `__name__` 与 `__doc__`。
