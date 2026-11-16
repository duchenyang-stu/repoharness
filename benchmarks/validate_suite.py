"""Validate an evaluation suite: every task must fail as shipped and pass with its reference solution.

This guards against broken tasks (already-passing, unsolvable, or hidden tests that do not bite).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoharness.evaluation import EvalCheck, EvalTask, evaluate_task  # noqa: E402


def main(suite_path: Path = ROOT / "evals" / "suite_v1.json") -> int:
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    suite_dir = suite_path.parent
    problems: list[str] = []
    for case in suite["tasks"]:
        task_id = case["id"]
        source = (suite_dir / case["workspace"]).resolve(strict=True)
        task = EvalTask(task_id, case["objective"], tuple(EvalCheck(**c) for c in case["checks"]))
        with tempfile.TemporaryDirectory() as directory:
            shipped = Path(directory) / "shipped"
            shutil.copytree(source, shipped)
            before = evaluate_task(shipped, task, source=source, suite_dir=suite_dir)
            kinds = {c["kind"]: c["passed"] for c in before.checks if c["kind"] in {"command", "hidden_test"}}
            if before.passed:
                problems.append(f"{task_id}: passes without any fix")
            if kinds.get("command") is True and not case.get("visible_tests_may_pass"):
                problems.append(f"{task_id}: visible tests already pass as shipped")
            if kinds.get("hidden_test") is True:
                problems.append(f"{task_id}: hidden tests already pass as shipped")
            if case.get("visible_tests_may_pass") and kinds.get("hidden_test") is not False:
                problems.append(f"{task_id}: visible tests may pass, so hidden tests must fail as shipped")

            solved = Path(directory) / "solved"
            shutil.copytree(source, solved)
            solution_dir = suite_dir / "solutions" / task_id
            for path in solution_dir.rglob("*"):
                if path.is_file():
                    target = solved / path.relative_to(solution_dir)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
            after = evaluate_task(solved, task, source=source, suite_dir=suite_dir)
            if not after.passed:
                failed = [c for c in after.checks if not c["passed"]]
                problems.append(f"{task_id}: reference solution fails {json.dumps(failed, ensure_ascii=False)[:400]}")
        print(f"{task_id:16s} tier={case.get('tier')} shipped_fails={not before.passed} solution_passes={after.passed}")
    if problems:
        print("\nPROBLEMS:")
        print("\n".join(problems))
        return 1
    print(f"\nall {len(suite['tasks'])} tasks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "evals" / "suite_v1.json"))
