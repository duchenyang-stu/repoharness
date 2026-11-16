"""Run a component ablation: the full harness vs. the harness with one component disabled, N rounds each.

Model, suite and budgets are held fixed; only the ablation switch changes between arms.

Usage:
  python benchmarks/run_ablation.py --suite evals/suite_v1.json --model <model> --rounds 3 \
      --output eval-results/ablation-1 [--arms full completion_gate read_before_write ...]
Then:
  python benchmarks/summarize_ablation.py eval-results/ablation-1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoharness.models import ABLATABLE_COMPONENTS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=None, help="Defaults to OPENAI_BASE_URL from the environment/.env")
    parser.add_argument("--output", required=True, help="Directory that will hold <arm>/run<k>/ reports")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-tool-calls", type=int, default=60)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--arms", nargs="+", default=["full", *ABLATABLE_COMPONENTS],
        help="'full' or any component name to disable (one component per arm)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the commands without running them")
    args = parser.parse_args()

    bad = [arm for arm in args.arms if arm != "full" and arm not in ABLATABLE_COMPONENTS]
    if bad:
        parser.error(f"unknown arm(s) {bad}; choose from full, {', '.join(ABLATABLE_COMPONENTS)}")

    output = Path(args.output).resolve()
    plan = []
    # Interleave arms within each round so provider drift/outages affect all arms alike.
    for round_index in range(1, args.rounds + 1):
        for arm in args.arms:
            target = output / ("full" if arm == "full" else f"no_{arm}") / f"run{round_index}"
            if (target / "report.json").exists():
                continue  # resume: already finished
            command = [
                sys.executable, "-m", "repoharness.cli", "eval", args.suite,
                "--output", str(target), "--model", args.model,
                "--max-steps", str(args.max_steps), "--max-tool-calls", str(args.max_tool_calls),
                "--timeout", str(args.timeout),
            ]
            if args.base_url:
                command += ["--base-url", args.base_url]
            if args.temperature is not None:
                command += ["--temperature", str(args.temperature)]
            if arm != "full":
                command += ["--disable", arm]
            plan.append((arm, round_index, target, command))

    print(f"{len(plan)} eval run(s) planned -> {output}")
    if args.dry_run:
        for arm, round_index, _, command in plan:
            print(f"[{arm} run{round_index}] " + " ".join(command))
        return 0

    env_pythonpath = str(ROOT / "src")
    failures = 0
    for arm, round_index, target, command in plan:
        if target.exists():  # partial leftovers from an interrupted run would trip run_suite's guard
            print(f"[{arm} run{round_index}] removing incomplete directory {target}")
            import shutil
            shutil.rmtree(target)
        print(f"[{arm} run{round_index}] start", flush=True)
        completed = subprocess.run(
            command, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": env_pythonpath},
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        (target.parent / f"run{round_index}.log").write_text(completed.stdout, encoding="utf-8")
        (target.parent / f"run{round_index}.err").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            failures += 1
            print(f"[{arm} run{round_index}] FAILED rc={completed.returncode}: {completed.stderr.strip()[-300:]}", flush=True)
        else:
            report = json.loads((target / "report.json").read_text(encoding="utf-8"))
            print(f"[{arm} run{round_index}] pass {report['passed']}/{report['task_count']}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
