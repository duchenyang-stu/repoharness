"""Aggregate ablation reports: per-arm metrics and paired differences against the full harness.

Usage: python benchmarks/summarize_ablation.py <ablation-output-dir> [--out docs/ablation-results.md]
Reads <dir>/<arm>/run<k>/report.json written by run_ablation.py.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def load(root: Path) -> dict[str, list[dict]]:
    arms: dict[str, list[dict]] = {}
    for arm_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        reports = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(arm_dir.glob("run*/report.json"))]
        if reports:
            arms[arm_dir.name] = reports
    return arms


def wilson(passed: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = passed / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def failure_kind(task: dict) -> str:
    if task["passed"]:
        return "ok"
    if task["run_status"] == "failed":
        error = task.get("error") or ""
        return "budget_or_runtime_error" if "budget" in error.lower() or "timeout" in error.lower() else "env_or_runtime_error"
    if task.get("verification_runs", 0) == 0:
        return "finished_without_verification"
    return "wrong_fix"


def rows_of(reports: list[dict]) -> list[dict]:
    return [t for r in reports for t in r["tasks"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    arms = load(Path(args.root))
    if "full" not in arms:
        raise SystemExit("No 'full' arm found; it is the baseline for paired comparison")

    first = arms["full"][0]
    lines = [f"模型：`{first['model']}`　套件：`{first['suite']}`　每个对照组轮数：{len(arms['full'])}\n"]
    lines.append("### 各对照组\n")
    lines.append("| 对照组 | 通过 (95% Wilson 区间) | 平均步数 | 平均工具调用 | 验证次数/任务 | 门禁拒绝 | 门禁被绕过(本应拒绝) | 平均 token | 平均耗时(s) |\n|---|---|---|---|---|---|---|---|---|\n")
    for arm, reports in arms.items():
        rows = rows_of(reports)
        n = len(rows)
        passed = sum(r["passed"] for r in rows)
        lo, hi = wilson(passed, n)
        lines.append(
            f"| {arm} | {passed}/{n} ({passed / n:.1%}; {lo:.0%}–{hi:.0%}) | "
            f"{statistics.fmean(r['steps'] for r in rows):.1f} | {statistics.fmean(r['tool_calls'] for r in rows):.1f} | "
            f"{statistics.fmean(r['verification_runs'] for r in rows):.2f} | "
            f"{sum(r['rejected_completions'] for r in rows)} | {sum(r.get('bypassed_rejections', 0) for r in rows)} | "
            f"{statistics.fmean(r['planner_usage'].get('total_tokens', 0) for r in rows):,.0f} | "
            f"{statistics.fmean(r['elapsed_seconds'] for r in rows):.1f} |\n"
        )

    lines.append("\n### 失败归类\n")
    kinds = ["ok", "wrong_fix", "finished_without_verification", "env_or_runtime_error", "budget_or_runtime_error"]
    lines.append("| 对照组 | " + " | ".join(kinds) + " |\n|---|" + "---|" * len(kinds) + "\n")
    for arm, reports in arms.items():
        counts = {k: 0 for k in kinds}
        for row in rows_of(reports):
            counts[failure_kind(row)] = counts.get(failure_kind(row), 0) + 1
        lines.append(f"| {arm} | " + " | ".join(str(counts[k]) for k in kinds) + " |\n")

    lines.append("\n### 与完整 Harness 的配对差异（按任务逐个比较，同一任务同一轮次）\n")
    lines.append("| 对照组 | 只在 full 通过 | 只在该组通过 | 两者都通过 | 两者都失败 | 通过率差 (该组 − full) |\n|---|---|---|---|---|---|\n")
    full_by_key = {(i, t["task_id"]): t["passed"] for i, r in enumerate(arms["full"]) for t in r["tasks"]}
    for arm, reports in arms.items():
        if arm == "full":
            continue
        only_full = only_arm = both = neither = 0
        for i, r in enumerate(reports):
            for t in r["tasks"]:
                f = full_by_key.get((i, t["task_id"]))
                if f is None:
                    continue
                if f and t["passed"]:
                    both += 1
                elif f:
                    only_full += 1
                elif t["passed"]:
                    only_arm += 1
                else:
                    neither += 1
        total = only_full + only_arm + both + neither
        diff = (only_arm - only_full) / total if total else 0.0
        lines.append(f"| {arm} | {only_full} | {only_arm} | {both} | {neither} | {diff:+.1%} |\n")
    lines.append(
        "\n> 解读提醒：若 full 与各对照组都接近满分，说明任务对该模型饱和，差异不可信；"
        "“门禁被绕过”为 0 说明该模型本来就会自行验证，门禁没有发挥机会。\n"
    )

    text = "".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
