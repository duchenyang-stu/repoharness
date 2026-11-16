def format_cents(cents):
    """仅用于展示，如 1999 -> '19.99'。"""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"
