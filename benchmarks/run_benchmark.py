"""Deterministic fault-injection benchmark for checkpoint recovery."""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoharness.models import PlannerTurn, RunStatus, ToolCall  # noqa: E402
from repoharness.planners import ScriptedPlanner  # noqa: E402
from repoharness.runtime import AgentRuntime  # noqa: E402
from repoharness.store import SQLiteRunStore  # noqa: E402
from repoharness.tools import build_repository_tools  # noqa: E402


def main(iterations: int = 100) -> dict:
    durations = []
    successful = 0
    duplicate_writes = 0
    for index in range(iterations):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "counter.txt"
            target.write_text("0", encoding="utf-8")
            store = SQLiteRunStore(root / "runs.db")
            turns = [
                PlannerTurn(calls=(ToolCall("write-once", "replace_text", {"path": "counter.txt", "old": "0", "new": "1"}),)),
                PlannerTurn(final_answer="complete"),
            ]
            runtime = AgentRuntime(store, build_repository_tools(root), ScriptedPlanner(turns))
            state = runtime.create_run(f"fault-injection-{index}", str(root))
            started = time.perf_counter()
            paused = runtime.run(state.run_id, interrupt_after_tool_calls=1)
            resumed = runtime.run(state.run_id)
            durations.append((time.perf_counter() - started) * 1000)
            successful += int(paused.status is RunStatus.PAUSED and resumed.status is RunStatus.SUCCEEDED)
            duplicate_writes += int(resumed.tool_calls != 1 or target.read_text() != "1")
            store.close()
    report = {
        "iterations": iterations,
        "successful_recoveries": successful,
        "recovery_rate": successful / iterations,
        "duplicate_write_failures": duplicate_writes,
        "latency_ms": {
            "p50": round(statistics.median(durations), 3),
            "p95": round(sorted(durations)[max(0, int(iterations * 0.95) - 1)], 3),
        },
        "scope": "local deterministic runtime; excludes LLM and network latency",
    }
    output = ROOT / "benchmarks" / "latest.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()

