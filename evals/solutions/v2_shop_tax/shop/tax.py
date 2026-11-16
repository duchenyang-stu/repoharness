from decimal import ROUND_HALF_UP, Decimal


def line_tax(amount_cents, rate):
    """返回一个商品行的税额（分），四舍五入（0.5 进位）。"""
    value = Decimal(amount_cents) * Decimal(str(rate))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
