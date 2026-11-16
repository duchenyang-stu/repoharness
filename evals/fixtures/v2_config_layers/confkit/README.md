# confkit

`load_config(schema, defaults, file_data, environ, prefix="APP_")` 合并三层配置，优先级从低到高：
**defaults < file_data < 环境变量**。

- `schema` 是 `{键名: 类型}`，类型为 `str` / `int` / `float` / `bool`。只处理 schema 中的键，其它键忽略。
- 环境变量名为 `prefix + 键名.upper()`，值一律是字符串，需要按类型解析。`file_data` 中的值若是字符串也要解析，
  若已经是正确的 Python 类型则原样使用。
- 布尔解析（不区分大小写，两侧空白忽略）：`1/true/yes/on` 为真，`0/false/no/off` 与空字符串为假，其它值视为非法。
- 数值解析失败（非法的布尔、无法转换的 int/float）时抛出 `ConfigError(key, message)`，其 `.key` 为出错的键名；
  不得悄悄回退到默认值。
- 某个 schema 键在三层中都没有值时，抛出 `ConfigError(key, "missing")`。
