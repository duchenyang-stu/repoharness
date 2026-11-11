def format_cents(cents):
    """把以分为单位的整数金额转成形如 '$12.50' 的字符串。"""
    return f"${cents // 100}.{cents % 100}"
