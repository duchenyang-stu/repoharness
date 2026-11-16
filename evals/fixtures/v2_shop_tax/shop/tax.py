def line_tax(amount_cents, rate):
    """返回一个商品行的税额（分）。"""
    return round(amount_cents * rate)
