"""Summarize an eval report.json into a Markdown table (overall, per tier, per task).

Usage: python benchmarks/summarize_eval.py <report.json> [--suite evals/suite_v1.json] [--out docs/eval-results.md]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarize(report: dict, tiers: dict[str, int]) -> str:
    tasks = report["tasks"]

    def agg(rows: list[dict]) -> str:
        n = len(rows)
        passed = sum(r["passed"] for r in rows)
        return (
            f"{passed}/{n} ({passed / n:.0%}) | {statistics.fmean(r['steps'] for r in rows):.1f} | "
            f"{statistics.fmean(r['tool_calls'] for r in rows):.1f} | "
            f"{sum(r['rejected_completions'] for r in rows)} | "
            f"{statistics.fmean(r['planner_usage'].get('total_tokens', 0) for r in rows):,.0f} | "
            f"{statistics.fmean(r['elapsed_seconds'] for r in rows):.1f}"
        )

    head = "| 通过 | 平均步数 | 平均工具调用 | 门禁拒绝次数 | 平均 token | 平均耗时(s) |\n|---|---|---|---|---|---|\n"
    lines = [f"模型：`{report['model']}`　套件：`{report['suite']}`　任务数：{len(tasks)}\n", "### 总体\n", head.replace("| 通过", "| 通过", 1)]
    lines[-1] = head + "| " + agg(tasks) + " |\n"
    lines.append("\n### 按难度分层\n")
    lines.append("| 难度 | " + head.split("\n")[0][2:] + "\n|---|---|---|---|---|---|---|\n")
    for tier in sorted(set(tiers.get(t["task_id"], 0) for t in tasks)):
        rows = [t for t in tasks if tiers.get(t["task_id"], 0) == tier]
        lines.append(f"| T{tier} | {agg(rows)} |\n")
    lines.append("\n### 各任务\n")
    lines.append("| 任务 | 难度 | 结果 | 运行状态 | 步数 | 工具调用 | 验证次数 | 门禁拒绝 | token | 耗时(s) | 未通过的检查 |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
    for t in tasks:
        failed = ", ".join(
            f"{c['kind']}" + (f":{c['path']}" if c.get("path") else "") for c in t["checks"] if not c["passed"]
        ) or "-"
        lines.append(
            f"| {t['task_id']} | T{tiers.get(t['task_id'], 0)} | {'通过' if t['passed'] else '失败'} | {t['run_status']} | "
            f"{t['steps']} | {t['tool_calls']} | {t['verification_runs']} | {t['rejected_completions']} | "
            f"{t['planner_usage'].get('total_tokens', 0):,} | {t['elapsed_seconds']:.1f} | {failed} |\n"
        )
    return "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--suite", default=str(ROOT / "evals" / "suite_v1.json"))
    parser.add_argument("--out")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    tiers = {t["id"]: t.get("tier", 0) for t in suite["tasks"]}
    text = summarize(report, tiers)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
