def flatten(xs):
    """把任意深度嵌套的列表展开成一维列表，保持顺序；字符串视为普通元素，不要拆开。"""
    out = []
    for x in xs:
        if isinstance(x, list):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out
