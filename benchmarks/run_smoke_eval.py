"""Run the bundled task-level smoke evaluation without model credentials."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoharness.evaluation import run_suite  # noqa: E402
from repoharness.models import PlannerTurn, ToolCall  # noqa: E402
from repoharness.planners import ScriptedPlanner  # noqa: E402
from repoharness.runtime import AgentRuntime  # noqa: E402
from repoharness.store import SQLiteRunStore  # noqa: E402
from repoharness.tools import build_repository_tools  # noqa: E402


def runtime_factory(workspace: Path) -> AgentRuntime:
    planner = ScriptedPlanner([
        PlannerTurn(calls=(ToolCall("overview", "repo_overview", {}),)),
        PlannerTurn(calls=(ToolCall("search", "search_repo", {"query": "return a - b"}),)),
        PlannerTurn(calls=(ToolCall("read", "read_file", {"path": "calc.py"}),)),
        PlannerTurn(calls=(ToolCall("patch", "apply_patch", {"changes": [{
            "path": "calc.py", "operation": "replace", "old": "return a - b", "new": "return a + b",
        }]}),)),
        PlannerTurn(calls=(ToolCall("diff", "get_diff", {}),)),
        PlannerTurn(calls=(ToolCall("verify", "run_tests", {"command": ["python", "-m", "unittest", "discover"]}),)),
        PlannerTurn(final_answer="Fixed addition and verified the focused test suite."),
    ])
    store = SQLiteRunStore(workspace / ".repoharness" / "runs.db")
    return AgentRuntime(store, build_repository_tools(workspace), planner)


def main() -> None:
    output = ROOT / "benchmarks" / f"smoke-eval-{int(time.time())}"
    result = run_suite(ROOT / "evals" / "smoke.json", output, "scripted-evaluator", runtime_factory)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
