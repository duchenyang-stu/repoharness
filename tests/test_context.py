from __future__ import annotations

import unittest

from repoharness.context import compact_messages, compact_tool_result


class ContextTests(unittest.TestCase):
    def test_large_tool_result_is_compacted_with_evidence(self):
        result = {"ok": True, "data": {"path": "a.py", "stdout": "x" * 20_000, "returncode": 0}}
        compacted = compact_tool_result(result, max_chars=1_000)
        self.assertTrue(compacted["truncated"])
        self.assertEqual(compacted["path"], "a.py")
        self.assertEqual(compacted["returncode"], 0)
        self.assertLessEqual(len(compacted["stdout"]), 3_000)

    def test_message_compaction_preserves_objective_and_recent_evidence(self):
        messages = [{"role": "user", "content": "fix bug"}]
        messages.extend({"role": "tool", "name": "read_file", "content": {"ok": True, "data": "x" * 2_000}} for _ in range(8))
        messages.append({"role": "tool", "name": "run_tests", "content": {"ok": False, "error": {"message": "failed"}}})
        compacted = compact_messages(messages, 4_000)
        self.assertEqual(compacted[0]["content"], "fix bug")
        self.assertTrue(any("Earlier context compacted" in str(item.get("content")) for item in compacted))
        self.assertEqual(compacted[-1]["name"], "run_tests")

    def test_compaction_keeps_assistant_tool_call_with_tool_result(self):
        messages = [{"role": "user", "content": "fix"}, {"role": "system", "content": "x" * 3_000}]
        messages.extend([
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": {"ok": True, "data": "y" * 1_000}},
        ])
        compacted = compact_messages(messages, 2_000)
        tool_index = next(index for index, item in enumerate(compacted) if item.get("role") == "tool")
        self.assertEqual(compacted[tool_index - 1]["role"], "assistant")
        self.assertEqual(compacted[tool_index - 1]["tool_calls"][0]["id"], "c1")


if __name__ == "__main__":
    unittest.main()
