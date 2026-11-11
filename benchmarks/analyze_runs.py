"""Decompose an eval run into process metrics and failure categories (read-only over event logs).

Pass rate alone says *whether* the agent succeeded. These metrics say *how*, so a bad result can be
traced to one harness component (gate, tools, context, limits) instead of "the harness is bad".

Usage: python benchmarks/analyze_runs.py <eval-output-dir> [<eval-output-dir> ...] [--suite evals/suite_v1.json] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTATE = {"replace_text", "apply_patch"}
VERIFY = {"run_tests"}


def load_events(db: Path) -> list[tuple[str, dict]]:
    connection = sqlite3.connect(db)
    try:
        rows = connection.execute("select kind, payload_json from events order by seq").fetchall()
    finally:
        connection.close()
    return [(kind, json.loads(payload)) for kind, payload in rows]


def analyze_task(events: list[tuple[str, dict]], graded_passed: bool) -> dict:
    tool_calls: list[dict] = []
    planner_prompt_tokens: list[int] = []
    rejected = 0
    run_error = None
    status = "unknown"
    for kind, payload in events:
        if kind == "tool.completed":
            tool_calls.append(payload)
        elif kind == "planner.completed":
            planner_prompt_tokens.append(payload.get("usage", {}).get("prompt_tokens", 0))
        elif kind == "completion.rejected":
            rejected += 1
        elif kind == "run.failed":
            run_error, status = payload.get("error", ""), "failed"
        elif kind == "run.succeeded":
            status = "succeeded"

    names = [call["name"] for call in tool_calls]
    failures = [call for call in tool_calls if not call["result"].get("ok")]
    policy_errors = sum(1 for call in failures if call["result"]["error"].get("type") == "PolicyError")

    mutation_indexes = [i for i, name in enumerate(names) if name in MUTATE and tool_calls[i]["result"].get("ok")]
    verify_indexes = [i for i, name in enumerate(names) if name in VERIFY]

    def verify_passed(index: int) -> bool:
        result = tool_calls[index]["result"]
        data = result.get("data", {}) if result.get("ok") else {}
        return bool(data.get("passed", data.get("returncode") == 0)) if result.get("ok") else False

    first_edit_verified_ok = None
    if mutation_indexes:
        after = [i for i in verify_indexes if i > mutation_indexes[0]]
        first_edit_verified_ok = verify_passed(after[0]) if after else False
    verified_after_last_edit = bool(mutation_indexes) and any(i > mutation_indexes[-1] for i in verify_indexes)

    reads = Counter(
        call.get("result", {}).get("data", {}).get("path") or call.get("arguments", {}).get("path")
        for call in tool_calls if call["name"] == "read_file"
    )
    reread = sum(count - 1 for count in reads.values() if count > 1)

    return {
        "status": status,
        "run_error": run_error,
        "graded_passed": graded_passed,
        "tool_calls": len(tool_calls),
        "tool_failures": len(failures),
        "policy_errors": policy_errors,
        "tool_failure_details": [
            f"{call['name']}|{call['result']['error'].get('type')}|{str(call['result']['error'].get('message'))[:80]}"
            for call in failures
        ],
        "exploration_calls_before_first_edit": mutation_indexes[0] if mutation_indexes else len(names),
        "mutations": len(mutation_indexes),
        "verifications": len(verify_indexes),
        "first_edit_verified_ok": first_edit_verified_ok,
        "verified_after_last_edit": verified_after_last_edit,
        "diff_reviewed": "get_diff" in names,
        "reread_calls": reread,
        "gate_rejections": rejected,
        "prompt_tokens_first_step": planner_prompt_tokens[0] if planner_prompt_tokens else 0,
        "prompt_tokens_last_step": planner_prompt_tokens[-1] if planner_prompt_tokens else 0,
        "failure_category": classify(status, run_error, graded_passed, mutation_indexes, verified_after_last_edit, verify_indexes, names, tool_calls),
    }


def classify(status, run_error, passed, mutations, verified_after_last, verifies, names, calls) -> str:
    """One mutually exclusive label per run; 'ok' when graded as passed and ended normally."""
    if status == "failed" and run_error:
        if any(token in run_error for token in ("URLError", "HTTPError", "timed out", "SSL", "Connection")):
            return "env_error_after_fix" if passed else "env_error"
        if "budget" in run_error or "timeout" in run_error:
            return "budget_exhausted"
        return "runtime_error"
    if passed:
        return "ok"
    if not mutations:
        return "no_edit"
    if not verifies or not verified_after_last:
        return "edit_without_final_verification"
    last_verify = verifies[-1]
    result = calls[last_verify]["result"]
    data = result.get("data", {}) if result.get("ok") else {}
    if not (bool(data.get("passed", data.get("returncode") == 0)) if result.get("ok") else False):
        return "verified_failing_but_stopped"
    return "visible_tests_pass_hidden_fail"


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)

    def mean(key):
        return round(statistics.fmean(row[key] for row in rows), 2)

    def rate(predicate):
        return round(sum(1 for row in rows if predicate(row)) / n, 3)

    edited = [row for row in rows if row["first_edit_verified_ok"] is not None]
    return {
        "runs": n,
        "graded_pass_rate": rate(lambda r: r["graded_passed"]),
        "tool_failure_rate": round(sum(r["tool_failures"] for r in rows) / max(1, sum(r["tool_calls"] for r in rows)), 3),
        "policy_errors_total": sum(r["policy_errors"] for r in rows),
        "gate_rejections_total": sum(r["gate_rejections"] for r in rows),
        "first_edit_correct_rate": round(sum(r["first_edit_verified_ok"] for r in edited) / max(1, len(edited)), 3),
        "verified_after_last_edit_rate": rate(lambda r: r["verified_after_last_edit"]),
        "diff_reviewed_rate": rate(lambda r: r["diff_reviewed"]),
        "mean_exploration_calls_before_first_edit": mean("exploration_calls_before_first_edit"),
        "mean_reread_calls": mean("reread_calls"),
        "mean_prompt_tokens_first_step": mean("prompt_tokens_first_step"),
        "mean_prompt_tokens_last_step": mean("prompt_tokens_last_step"),
        "failure_categories": dict(Counter(r["failure_category"] for r in rows)),
        "tool_failure_breakdown": dict(Counter(d for r in rows for d in r["tool_failure_details"]).most_common()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--suite", default=str(ROOT / "evals" / "suite_v1.json"))
    parser.add_argument("--json")
    args = parser.parse_args()
    tiers = {t["id"]: t.get("tier", 0) for t in json.loads(Path(args.suite).read_text(encoding="utf-8"))["tasks"]}
    rows: list[dict] = []
    for directory in map(Path, args.dirs):
        report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        for task in report["tasks"]:
            events = load_events(directory / "workspaces" / task["task_id"] / ".repoharness" / "runs.db")
            row = analyze_task(events, task["passed"])
            row.update(task_id=task["task_id"], tier=tiers.get(task["task_id"], 0), run=directory.name)
            rows.append(row)
    result = {"overall": aggregate(rows), "by_tier": {f"T{t}": aggregate([r for r in rows if r["tier"] == t]) for t in sorted({r["tier"] for r in rows})}, "runs": rows}
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"overall": result["overall"], "by_tier": result["by_tier"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
