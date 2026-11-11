import re

_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text):
    """把形如 '1h30m'、'45s' 的时长字符串转成秒数。支持 h、m、s，可组合。"""
    total = 0
    for number, unit in re.findall(r"(\d+)([hms])", text):
        total += int(number) * _UNITS[unit]
    return total
