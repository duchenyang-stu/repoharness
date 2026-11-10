"""Command-line demo and API launcher."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .models import Budget, PlannerTurn, ToolCall
from .planners import OpenAICompatiblePlanner, ScriptedPlanner
from .runtime import AgentRuntime
from .store import SQLiteRunStore
from .tools import build_repository_tools
from .env import load_env
from .evaluation import run_suite


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="RepoHarness repository-agent runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Run a deterministic inspect/test workflow")
    demo.add_argument("workspace")
    demo.add_argument("--query", default="TODO")
    live = subparsers.add_parser("run", help="Run with an OpenAI-compatible model")
    live.add_argument("workspace")
    live.add_argument("objective")
    live.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    live.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    live.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    evaluate = subparsers.add_parser("eval", help="Run an isolated task-level repository-agent evaluation suite")
    evaluate.add_argument("suite", help="Path to an evaluation suite JSON file")
    evaluate.add_argument("--output", default="eval-results")
    evaluate.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    evaluate.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    evaluate.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""))
    evaluate.add_argument("--max-steps", type=int, default=30)
    evaluate.add_argument("--max-tool-calls", type=int, default=60)
    evaluate.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()

    if args.command == "eval":
        if not args.api_key:
            parser.error("--api-key or OPENAI_API_KEY is required")
        budget = Budget(
            max_steps=args.max_steps,
            max_tool_calls=args.max_tool_calls,
            timeout_seconds=args.timeout,
        )

        def runtime_factory(eval_workspace: Path) -> AgentRuntime:
            store = SQLiteRunStore(eval_workspace / ".repoharness" / "runs.db")
            planner = OpenAICompatiblePlanner(
                args.base_url, args.api_key, args.model,
                max_context_chars=budget.max_context_chars,
            )
            return AgentRuntime(store, build_repository_tools(eval_workspace), planner, budget)

        report = run_suite(args.suite, args.output, args.model, runtime_factory)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return

    workspace = str(Path(args.workspace).resolve())
    store = SQLiteRunStore(Path(workspace) / ".repoharness" / "runs.db")
    tools = build_repository_tools(workspace)
    if args.command == "demo":
        planner = ScriptedPlanner([
            PlannerTurn(calls=(ToolCall("demo-search", "search_repo", {"query": args.query, "limit": 10}),)),
            PlannerTurn(calls=(ToolCall("demo-changes", "get_changes", {}),)),
            PlannerTurn(final_answer="Repository inspection completed; see persisted events for evidence."),
        ])
        objective = f"Inspect the repository for {args.query!r}"
    else:
        if not args.api_key:
            parser.error("--api-key or OPENAI_API_KEY is required")
        planner = OpenAICompatiblePlanner(args.base_url, args.api_key, args.model)
        objective = args.objective
    runtime = AgentRuntime(store, tools, planner)
    state = runtime.create_run(objective, workspace)
    final = runtime.run(state.run_id)
    print(json.dumps(final.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

