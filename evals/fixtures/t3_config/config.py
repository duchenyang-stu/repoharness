def merge_config(defaults, overrides):
    """用 overrides 覆盖 defaults，返回新字典。嵌套字典要递归合并；列表整体替换；不能修改传入的参数。"""
    merged = defaults
    merged.update(overrides)
    return merged
