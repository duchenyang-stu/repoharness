def is_palindrome(s):
    """判断字符串是否为回文：忽略大小写，并且忽略所有非字母数字字符。"""
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
