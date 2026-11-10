from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repoharness.models import Budget, PlannerTurn, RunStatus, ToolCall
from repoharness.planners import ScriptedPlanner
from repoharness.runtime import AgentRuntime
from repoharness.store import SQLiteRunStore
from repoharness.tools import build_repository_tools


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "value.txt").write_text("before", encoding="utf-8")
        (self.root / "test_smoke.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n",
            encoding="utf-8",
        )
        self.store = SQLiteRunStore(self.root / "runs.db")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def runtime(self, turns, budget=None):
        return AgentRuntime(self.store, build_repository_tools(self.root), ScriptedPlanner(turns), budget)

    def test_run_persists_events_and_succeeds(self):
        runtime = self.runtime([
            PlannerTurn(calls=(ToolCall("read-1", "read_file", {"path": "value.txt"}),)),
            PlannerTurn(final_answer="done"),
        ])
        state = runtime.create_run("read it", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertGreaterEqual(len(list(self.store.events(state.run_id))), 4)
        self.assertIn("tool_calls", result.messages[1])

    def test_resume_does_not_repeat_mutation(self):
        turns = [
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("edit-1", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("verify-1", "run_tests", {}),)),
            PlannerTurn(final_answer="fixed"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("fix it", str(self.root))
        paused = runtime.run(state.run_id, interrupt_after_tool_calls=1)
        self.assertEqual(paused.status, RunStatus.PAUSED)
        resumed = runtime.run(state.run_id)
        self.assertEqual(resumed.status, RunStatus.SUCCEEDED)
        self.assertEqual((self.root / "value.txt").read_text(), "after")
        self.assertEqual(resumed.tool_calls, 3)
        self.assertTrue(resumed.last_verification_passed)

    def test_duplicate_call_id_returns_cached_result(self):
        turns = [
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("verify", "run_tests", {}),)),
            PlannerTurn(final_answer="done"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("idempotent", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertEqual((self.root / "value.txt").read_text(), "after")
        self.assertEqual(result.tool_calls, 3)
        events = list(self.store.events(state.run_id))
        self.assertTrue(any(e["payload"].get("replayed") for e in events if e["kind"] == "tool.completed"))

    def test_duplicate_call_id_with_different_arguments_is_rejected(self):
        turns = [
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "broken"}),)),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("reject call collision", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertIn("reused with different arguments", result.error)
        self.assertEqual((self.root / "value.txt").read_text(encoding="utf-8"), "after")

    def test_completion_is_rejected_until_post_edit_verification_passes(self):
        turns = [
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("edit", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(final_answer="premature"),
            PlannerTurn(calls=(ToolCall("verify", "run_tests", {}),)),
            PlannerTurn(final_answer="verified"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("fix and verify", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertEqual(result.final_answer, "verified")
        self.assertEqual(result.rejected_completions, 1)
        self.assertTrue(any(e["kind"] == "completion.rejected" for e in self.store.events(state.run_id)))

    def test_edit_is_blocked_until_repository_overview(self):
        turns = [
            PlannerTurn(calls=(ToolCall("early-edit", "replace_text", {"path": "value.txt", "old": "before", "new": "bad"}),)),
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("edit", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("verify", "run_tests", {}),)),
            PlannerTurn(final_answer="done"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("inspect first", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertEqual((self.root / "value.txt").read_text(encoding="utf-8"), "after")
        tool_events = [e for e in self.store.events(state.run_id) if e["kind"] == "tool.completed"]
        self.assertEqual(tool_events[0]["payload"]["result"]["error"]["type"], "PolicyError")

    def test_edit_and_verification_in_same_planner_turn_can_complete(self):
        turns = [
            PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
            PlannerTurn(calls=(
                ToolCall("edit", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),
                ToolCall("verify", "run_tests", {}),
            )),
            PlannerTurn(final_answer="done"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("multi call", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertEqual(result.rejected_completions, 0)
        self.assertGreater(result.last_verification_tool_call, result.last_mutation_tool_call)

    def test_step_budget_terminates_loop(self):
        runtime = self.runtime([
            PlannerTurn(calls=(ToolCall("one", "get_changes", {}),)),
            PlannerTurn(calls=(ToolCall("two", "get_changes", {}),)),
        ], Budget(max_steps=1, max_tool_calls=10, timeout_seconds=10))
        state = runtime.create_run("loop", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertIn("Step budget", result.error)

    def test_cancelled_run_is_terminal(self):
        runtime = self.runtime([PlannerTurn(final_answer="should not run")])
        state = runtime.create_run("cancel", str(self.root))
        runtime.cancel(state.run_id)
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()

