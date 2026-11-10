from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repoharness.tools import build_repository_tools


class RepositoryToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "calc.py").write_text("def add(a, b):\n    return a - b  # BUG\n", encoding="utf-8")
        self.tools = build_repository_tools(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_search_returns_file_and_line(self):
        result = self.tools.get("search_repo").invoke({"query": "BUG"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["matches"][0]["line"], 2)

    def test_search_skips_binary_and_runtime_state(self):
        (self.root / "binary.db").write_bytes(b"BUG\x00binary")
        state_dir = self.root / ".repoharness"
        state_dir.mkdir()
        (state_dir / "events.txt").write_text("BUG", encoding="utf-8")
        result = self.tools.get("search_repo").invoke({"query": "BUG"})
        paths = {item["path"] for item in result["data"]["matches"]}
        self.assertEqual(paths, {"calc.py"})

    def test_read_is_bounded(self):
        result = self.tools.get("read_file").invoke({"path": "calc.py", "start_line": 2, "end_line": 9999})
        self.assertEqual(result["data"]["total_lines"], 2)
        self.assertEqual(len(result["data"]["lines"]), 1)

    def test_path_traversal_is_rejected(self):
        result = self.tools.get("read_file").invoke({"path": "../secret.txt"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "PermissionError")

    def test_managed_path_is_rejected(self):
        managed = self.root / ".repoharness"
        managed.mkdir()
        (managed / "runs.db").write_text("secret", encoding="utf-8")
        result = self.tools.get("read_file").invoke({"path": ".repoharness/runs.db"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "PermissionError")

    def test_replace_uses_optimistic_count(self):
        result = self.tools.get("replace_text").invoke({"path": "calc.py", "old": "a - b", "new": "a + b"})
        self.assertTrue(result["ok"])
        self.assertIn("a + b", (self.root / "calc.py").read_text())

    def test_replace_rejects_stale_edit(self):
        result = self.tools.get("replace_text").invoke({"path": "calc.py", "old": "missing", "new": "x"})
        self.assertFalse(result["ok"])

    def test_shell_executable_is_rejected(self):
        result = self.tools.get("run_tests").invoke({"command": ["cmd", "/c", "echo unsafe"]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "PermissionError")

    def test_unittest_command_runs_without_shell(self):
        (self.root / "test_ok.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
            encoding="utf-8",
        )
        result = self.tools.get("run_tests").invoke({"command": ["python", "-m", "unittest", "discover"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["returncode"], 0)
        self.assertTrue(result["data"]["passed"])

    def test_unittest_with_zero_tests_is_not_valid_verification(self):
        result = self.tools.get("run_tests").invoke({"command": ["python", "-m", "unittest", "discover"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["returncode"], 0)
        self.assertFalse(result["data"]["passed"])
        self.assertTrue(result["data"]["zero_tests_detected"])

    def test_inline_python_is_rejected(self):
        result = self.tools.get("run_tests").invoke({"command": ["python", "-c", "print('unsafe')"]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "PermissionError")

    def test_repo_overview_finds_manifest_tests_and_languages(self):
        (self.root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_calc.py").write_text("def test_add(): pass\n", encoding="utf-8")
        result = self.tools.get("repo_overview").invoke({})
        self.assertTrue(result["ok"])
        self.assertIn("pyproject.toml", result["data"]["manifests"])
        self.assertIn("tests/test_calc.py", result["data"]["test_files"])
        self.assertIn((".py", 2), [tuple(item) for item in result["data"]["language_extensions"]])

    def test_apply_patch_validates_multiple_files_and_exposes_diff(self):
        result = self.tools.get("apply_patch").invoke({"changes": [
            {"path": "calc.py", "operation": "replace", "old": "a - b", "new": "a + b"},
            {"path": "tests/test_calc.py", "operation": "create", "content": "def test_add():\n    assert True\n"},
        ]})
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["validated_before_write"])
        self.assertTrue(result["data"]["rollback_on_write_error"])
        self.assertEqual(len(result["data"]["changed_files"]), 2)
        diff = self.tools.get("get_diff").invoke({})
        self.assertEqual(diff["data"]["changed_file_count"], 2)
        self.assertIn("+    return a + b", diff["data"]["diff"])
        self.assertIn("+++ b/tests/test_calc.py", diff["data"]["diff"])

    def test_apply_patch_rolls_back_all_files_if_any_change_is_stale(self):
        original = (self.root / "calc.py").read_text(encoding="utf-8")
        result = self.tools.get("apply_patch").invoke({"changes": [
            {"path": "new.py", "operation": "create", "content": "created = True\n"},
            {"path": "calc.py", "operation": "replace", "old": "missing", "new": "x"},
        ]})
        self.assertFalse(result["ok"])
        self.assertFalse((self.root / "new.py").exists())
        self.assertEqual((self.root / "calc.py").read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()

