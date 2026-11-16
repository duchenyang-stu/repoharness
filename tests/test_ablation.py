from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from repoharness.models import Ablation, PlannerTurn, RunState, RunStatus, ToolCall
from repoharness.planners import OpenAICompatiblePlanner, ScriptedPlanner
from repoharness.runtime import AgentRuntime
from repoharness.store import SQLiteRunStore
from repoharness.tools import build_repository_tools


class AblationTests(unittest.TestCase):
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

    def run_turns(self, turns, ablation=None):
        runtime = AgentRuntime(self.store, build_repository_tools(self.root), ScriptedPlanner(turns), ablation=ablation)
        state = runtime.create_run("task", str(self.root))
        return runtime.run(state.run_id)

    @staticmethod
    def edit_then_finish_without_verifying():
        return [
            PlannerTurn(calls=(ToolCall("ov", "repo_overview", {}),)),
            PlannerTurn(calls=(ToolCall("ed", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(final_answer="done"),
            PlannerTurn(calls=(ToolCall("vf", "run_tests", {}),)),
            PlannerTurn(final_answer="done after verifying"),
        ]

    def test_full_harness_rejects_unverified_completion(self):
        final = self.run_turns(self.edit_then_finish_without_verifying())
        self.assertEqual(final.status, RunStatus.SUCCEEDED)
        self.assertEqual(final.rejected_completions, 1)
        self.assertEqual(final.bypassed_rejections, 0)
        self.assertEqual(final.final_answer, "done after verifying")

    def test_gate_ablation_lets_unverified_completion_through_and_counts_it(self):
        final = self.run_turns(self.edit_then_finish_without_verifying(), Ablation.disabling("completion_gate"))
        self.assertEqual(final.status, RunStatus.SUCCEEDED)
        self.assertEqual(final.rejected_completions, 0)
        self.assertEqual(final.bypassed_rejections, 1)
        self.assertEqual(final.final_answer, "done")
        self.assertEqual(final.verification_runs, 0)
        events = [e["kind"] for e in self.store.events(final.run_id)]
        self.assertIn("completion.gate_bypassed", events)

    def test_read_before_write_ablation_allows_edit_without_overview(self):
        turns = [
            PlannerTurn(calls=(ToolCall("ed", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(calls=(ToolCall("vf", "run_tests", {}),)),
            PlannerTurn(final_answer="done"),
        ]
        final = self.run_turns(turns, Ablation.disabling("read_before_write"))
        self.assertEqual((self.root / "value.txt").read_text(), "after")
        self.assertEqual(final.status, RunStatus.SUCCEEDED)

    def test_read_before_write_enforced_by_default(self):
        turns = [
            PlannerTurn(calls=(ToolCall("ed", "replace_text", {"path": "value.txt", "old": "before", "new": "after"}),)),
            PlannerTurn(final_answer="done"),
        ]
        self.run_turns(turns)
        self.assertEqual((self.root / "value.txt").read_text(), "before")

    def test_tool_result_compaction_can_be_disabled(self):
        (self.root / "test_noisy.py").write_text(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_noise(self):\n"
            "        print('y' * 40000)\n",
            encoding="utf-8",
        )
        turns = lambda: [
            PlannerTurn(calls=(ToolCall("vf", "run_tests", {}),)),
            PlannerTurn(final_answer="ok"),
        ]

        def tool_message(state):
            return next(m for m in state.messages if m.get("role") == "tool")["content"]

        compacted = tool_message(self.run_turns(turns()))
        self.assertTrue(compacted.get("truncated"))
        self.store.close()
        self.store = SQLiteRunStore(self.root / "runs2.db")
        raw = tool_message(self.run_turns(turns(), Ablation.disabling("compact_tool_results")))
        self.assertFalse(raw.get("truncated", False))
        self.assertGreater(len(json.dumps(raw)), 10_000)

    def test_unknown_component_and_labels(self):
        with self.assertRaises(ValueError):
            Ablation.disabling("nonsense")
        self.assertEqual(Ablation().label, "full")
        self.assertEqual(Ablation.disabling("completion_gate").label, "no_completion_gate")
        self.assertEqual(
            Ablation.disabling("completion_gate", "compact_context").label,
            "no_completion_gate+compact_context",
        )


class PlannerRetryTests(unittest.TestCase):
    @staticmethod
    def ok_response():
        body = json.dumps({
            "choices": [{"message": {"content": "all done"}}],
            "usage": {"total_tokens": 5},
        }).encode()
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(body)
        return response

    def planner(self, **kwargs):
        return OpenAICompatiblePlanner("http://x/v1", "k", "m", retry_backoff_seconds=0.0, **kwargs)

    def state(self):
        s = RunState(run_id="r", objective="o", workspace=".")
        s.messages.append({"role": "user", "content": "o"})
        return s

    def test_transient_errors_are_retried(self):
        responses = [urllib.error.URLError("ssl eof"), urllib.error.URLError("ssl eof"), self.ok_response()]
        planner = self.planner()
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            turn = planner.next_turn(self.state(), [])
        self.assertEqual(turn.final_answer, "all done")
        self.assertEqual(planner.retries_used, 2)

    def test_retries_are_bounded(self):
        planner = self.planner(max_retries=2)
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")) as urlopen:
            with self.assertRaises(urllib.error.URLError):
                planner.next_turn(self.state(), [])
        self.assertEqual(urlopen.call_count, 3)

    def test_client_errors_are_not_retried(self):
        error = urllib.error.HTTPError("http://x", 401, "unauthorized", {}, io.BytesIO(b""))
        planner = self.planner()
        with mock.patch("urllib.request.urlopen", side_effect=error) as urlopen:
            with self.assertRaises(urllib.error.HTTPError):
                planner.next_turn(self.state(), [])
        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
