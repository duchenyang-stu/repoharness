def average(nums):
    """返回数字列表的算术平均值；空列表抛出 ValueError。"""
    if not nums:
        raise ValueError("empty list")
    return sum(nums) / len(nums)
