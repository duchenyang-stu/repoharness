from decimal import Decimal, InvalidOperation


def parse_amount(text):
    """'19.99' -> 1999，必须精确，最多两位小数。"""
    try:
        cents = Decimal(text.strip()) * 100
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {text!r}") from exc
    if cents != cents.to_integral_value():
        raise ValueError(f"amount has more than two decimals: {text!r}")
    return int(cents)
