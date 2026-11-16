_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def parse_value(typ, raw):
    if not isinstance(raw, str):
        return raw
    if typ is bool:
        text = raw.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError(f"invalid boolean: {raw!r}")
    if typ is int:
        return int(raw)
    if typ is float:
        return float(raw)
    return raw
