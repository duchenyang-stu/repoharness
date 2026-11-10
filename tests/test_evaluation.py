from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repoharness.evaluation import EvalCheck, EvalTask, evaluate_task, run_suite
from repoharness.models import PlannerTurn, ToolCall
from repoharness.planners import ScriptedPlanner
from repoharness.runtime import AgentRuntime
from repoharness.store import SQLiteRunStore
from repoharness.tools import build_repository_tools


class EvaluationTests(unittest.TestCase):
    def test_grades_repository_state_independently_of_agent_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "calc.py").write_text("return a + b\n", encoding="utf-8")
            (root / "test_ok.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            task = EvalTask("fix-add", "repair addition", (
                EvalCheck("file_contains", path="calc.py", value="a + b"),
                EvalCheck("file_not_contains", path="calc.py", value="a - b"),
                EvalCheck("command", command=["python", "-m", "unittest", "discover"]),
            ))
            result = evaluate_task(root, task)
            self.assertTrue(result.passed)
            self.assertEqual(len(result.checks), 3)

    def test_suite_runs_in_isolation_and_reports_task_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            (source / "test_calc.py").write_text(
                "import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(2, 3), 5)\n",
                encoding="utf-8",
            )
            suite = root / "suite.json"
            suite.write_text(__import__("json").dumps({
                "name": "smoke",
                "tasks": [{
                    "id": "fix-add",
                    "workspace": str(source),
                    "objective": "Fix add and verify it",
                    "checks": [
                        {"kind": "file_contains", "path": "calc.py", "value": "a + b"},
                        {"kind": "command", "command": ["python", "-m", "unittest", "discover"]},
                    ],
                }],
            }), encoding="utf-8")

            def runtime_factory(workspace: Path) -> AgentRuntime:
                turns = [
                    PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
                    PlannerTurn(calls=(ToolCall("edit", "apply_patch", {"changes": [{
                        "path": "calc.py", "operation": "replace", "old": "a - b", "new": "a + b",
                    }]}),)),
                    PlannerTurn(calls=(ToolCall("diff", "get_diff", {}),)),
                    PlannerTurn(calls=(ToolCall("tests", "run_tests", {"command": ["python", "-m", "unittest", "discover"]}),)),
                    PlannerTurn(final_answer="Fixed and verified."),
                ]
                store = SQLiteRunStore(workspace / ".repoharness" / "runs.db")
                return AgentRuntime(store, build_repository_tools(workspace), ScriptedPlanner(turns))

            result = run_suite(suite, root / "results", "scripted", runtime_factory).to_dict()
            self.assertEqual(result["pass_rate"], 1.0)
            self.assertEqual(result["tasks"][0]["verification_runs"], 1)
            self.assertEqual(result["tasks"][0]["tool_calls"], 4)
            self.assertTrue((root / "results" / "report.json").is_file())


if __name__ == "__main__":
    unittest.main()
