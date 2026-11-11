import re


def word_count(text):
    """统计单词出现次数。单词是连续的字母或数字；大小写不敏感，结果的键为小写。"""
    counts = {}
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        counts[word] = counts.get(word, 0) + 1
    return counts
