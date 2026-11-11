from datetime import timedelta


def week_start(d):
    """返回 d 所在周的周一（ISO 周，周一为一周的第一天）。"""
    return d - timedelta(days=d.weekday())


def weeks_between(a, b):
    """返回 a 与 b 之间相隔的周数（按 ISO 周计：两者所在周的周一相差几周）。a 不晚于 b。"""
    return (week_start(b) - week_start(a)).days // 7
