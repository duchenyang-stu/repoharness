def parse_amount(text):
    """'19.99' -> 1999"""
    return int(float(text) * 100)
