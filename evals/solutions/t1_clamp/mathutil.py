def clamp(x, lo, hi):
    """把 x 限制在 [lo, hi] 区间内。"""
    return max(lo, min(x, hi))
