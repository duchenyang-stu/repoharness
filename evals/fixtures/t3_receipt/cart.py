def total_cents(items):
    """items 是 {'name', 'price_cents', 'qty'} 的列表，返回总价（分）。"""
    return sum(item["price_cents"] for item in items)
