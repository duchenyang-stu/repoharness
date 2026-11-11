def merge_intervals(intervals):
    """合并闭区间 (start, end)：相交或首尾相接（如 (1, 3) 与 (3, 4)）的区间要合并。

    返回按起点排序的新列表；不要修改传入的参数。
    """
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged
