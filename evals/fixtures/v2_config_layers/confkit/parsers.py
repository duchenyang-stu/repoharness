def parse_value(typ, raw):
    if typ is bool:
        return bool(raw)
    if typ is int:
        try:
            return int(raw)
        except ValueError:
            return 0
    if typ is float:
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return str(raw)
