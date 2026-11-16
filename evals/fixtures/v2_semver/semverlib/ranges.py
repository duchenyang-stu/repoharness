from .version import Version


def satisfies(version, constraint):
    """仅支持 '>=x.y.z' / '<=' / '>' / '<' / '==' 这类单个比较。"""
    for op in (">=", "<=", ">", "<", "=="):
        if constraint.startswith(op):
            other = Version(constraint[len(op):])
            if op == ">=":
                return not version < other
            if op == "<=":
                return not other < version
            if op == ">":
                return other < version
            if op == "<":
                return version < other
            return version == other
    raise ValueError(f"unsupported constraint: {constraint!r}")
