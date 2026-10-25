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
            PlannerTurn(calls=(ToolCall("edit-1", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(final_answer="fixed"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("fix it", str(self.root))
        paused = runtime.run(state.run_id, interrupt_after_tool_calls=1)
        self.assertEqual(paused.status, RunStatus.PAUSED)
        resumed = runtime.run(state.run_id)
        self.assertEqual(resumed.status, RunStatus.SUCCEEDED)
        self.assertEqual((self.root / "value.txt").read_text(), "after")
        self.assertEqual(resumed.tool_calls, 1)

    def test_duplicate_call_id_returns_cached_result(self):
        turns = [
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("same", "replace_text", {"path": "value.txt", "old": "before", "new": "broken"}),)),
            PlannerTurn(final_answer="done"),
        ]
        runtime = self.runtime(turns)
        state = runtime.create_run("idempotent", str(self.root))
        result = runtime.run(state.run_id)
        self.assertEqual(result.status, RunStatus.SUCCEEDED)
        self.assertEqual((self.root / "value.txt").read_text(), "after")
        self.assertEqual(result.tool_calls, 1)
        events = list(self.store.events(state.run_id))
        self.assertTrue(any(e["payload"].get("replayed") for e in events if e["kind"] == "tool.completed"))

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

