import unittest

from config import merge_config


class HiddenConfig(unittest.TestCase):
    def test_lists_are_replaced(self):
        self.assertEqual(merge_config({"tags": ["a", "b"]}, {"tags": ["c"]}), {"tags": ["c"]})

    def test_result_is_independent_copy(self):
        defaults = {"a": {"b": {"c": 1}}}
        result = merge_config(defaults, {})
        result["a"]["b"]["c"] = 99
        self.assertEqual(defaults["a"]["b"]["c"], 1)

    def test_overrides_not_mutated(self):
        overrides = {"a": {"b": 2}}
        result = merge_config({"a": {"x": 1}}, overrides)
        result["a"]["b"] = 3
        self.assertEqual(overrides, {"a": {"b": 2}})

    def test_new_nested_keys(self):
        self.assertEqual(merge_config({}, {"a": {"b": 1}}), {"a": {"b": 1}})

    def test_dict_overridden_by_scalar(self):
        self.assertEqual(merge_config({"a": {"b": 1}}, {"a": 5}), {"a": 5})
