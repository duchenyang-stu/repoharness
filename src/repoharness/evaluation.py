"""Task-level evaluation primitives for repository-agent runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import shutil
import statistics
from pathlib import Path
from typing import Any

from .sandbox import WorkspaceSandbox


@dataclass(frozen=True)
class EvalCheck:
    kind: str
    path: str | None = None
    value: str | None = None
    command: list[str] | None = None


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    objective: str
    checks: tuple[EvalCheck, ...]


@dataclass
class EvalResult:
    task_id: str
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteResult:
    suite: str
    model: str
    tasks: list[dict[str, Any]]
    ablation: str = "full"

    def to_dict(self) -> dict[str, Any]:
        passed = sum(1 for item in self.tasks if item["passed"])
        count = len(self.tasks)
        return {
            "suite": self.suite,
            "model": self.model,
            "ablation": self.ablation,
            "task_count": count,
            "passed": passed,
            "pass_rate": passed / count if count else 0.0,
            "mean_steps": statistics.fmean(item["steps"] for item in self.tasks) if count else 0.0,
            "mean_tool_calls": statistics.fmean(item["tool_calls"] for item in self.tasks) if count else 0.0,
            "total_prompt_tokens": sum(item["planner_usage"].get("prompt_tokens", 0) for item in self.tasks),
            "total_completion_tokens": sum(item["planner_usage"].get("completion_tokens", 0) for item in self.tasks),
            "tasks": self.tasks,
        }


HIDDEN_TEST_MODULE = "hidden_check_test"


def evaluate_task(
    workspace: str | Path,
    task: EvalTask,
    *,
    source: str | Path | None = None,
    suite_dir: str | Path | None = None,
) -> EvalResult:
    """Grade final repository state independently from the model's final answer.

    ``source`` is the pristine task workspace (for ``file_unchanged``); ``suite_dir`` is the
    directory holding hidden tests (for ``hidden_test``). Both stay invisible to the agent.
    """
    sandbox = WorkspaceSandbox(workspace)
    results: list[dict[str, Any]] = []
    for check in task.checks:
        if check.kind in {"file_contains", "file_not_contains"}:
            if not check.path or check.value is None:
                raise ValueError(f"{check.kind} requires path and value")
            path = sandbox.resolve(check.path, must_exist=True)
            content = path.read_text(encoding="utf-8", errors="replace")
            found = check.value in content
            passed = found if check.kind == "file_contains" else not found
            results.append({"kind": check.kind, "path": check.path, "passed": passed})
        elif check.kind in {"file_exists", "file_not_exists"}:
            if not check.path:
                raise ValueError(f"{check.kind} requires path")
            path = sandbox.resolve(check.path, must_exist=False)
            exists = path.exists()
            passed = exists if check.kind == "file_exists" else not exists
            results.append({"kind": check.kind, "path": check.path, "passed": passed})
        elif check.kind == "file_unchanged":
            if source is None or not check.path:
                raise ValueError("file_unchanged requires path and a pristine source workspace")
            original = (Path(source) / check.path).read_bytes()
            current = sandbox.resolve(check.path, must_exist=True).read_bytes()
            results.append({"kind": "file_unchanged", "path": check.path, "passed": original == current})
        elif check.kind == "hidden_test":
            if suite_dir is None or not check.path:
                raise ValueError("hidden_test requires path and a suite directory")
            hidden = (Path(suite_dir) / check.path).resolve(strict=True)
            target = sandbox.root / f"{HIDDEN_TEST_MODULE}.py"
            shutil.copyfile(hidden, target)
            try:
                completed = sandbox.run(["python", "-m", "unittest", HIDDEN_TEST_MODULE], 300)
            finally:
                target.unlink(missing_ok=True)
            results.append({
                "kind": "hidden_test", "path": check.path, "passed": completed.returncode == 0,
                "returncode": completed.returncode, "stderr_tail": completed.stderr[-1500:],
            })
        elif check.kind == "command":
            if not check.command:
                raise ValueError("command check requires a command")
            completed = sandbox.run(check.command, 300)
            results.append({
                "kind": "command", "command": check.command, "passed": completed.returncode == 0,
                "returncode": completed.returncode, "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-2000:],
            })
        else:
            raise ValueError(f"Unknown evaluation check: {check.kind}")
    return EvalResult(task.task_id, all(item["passed"] for item in results), results)


def load_suite(path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw.get("tasks"), list) or not raw["tasks"]:
        raise ValueError("Evaluation suite must contain a non-empty tasks array")
    return str(raw.get("name", Path(path).stem)), raw["tasks"]


def run_suite(
    suite_path: str | Path,
    output_root: str | Path,
    model: str,
    runtime_factory,
    ablation: str = "full",
) -> SuiteResult:
    """Run each task in an isolated workspace copy and grade final state with hidden checks."""
    suite_file = Path(suite_path).expanduser().resolve(strict=True)
    suite_name, cases = load_suite(suite_file)
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    task_results: list[dict[str, Any]] = []
    for case in cases:
        task_id = str(case["id"])
        source_value = Path(case["workspace"]).expanduser()
        source = (suite_file.parent / source_value).resolve(strict=True) if not source_value.is_absolute() else source_value.resolve(strict=True)
        workspace = output / "workspaces" / task_id
        if workspace.exists():
            raise FileExistsError(f"Evaluation workspace already exists: {workspace}")
        shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", ".repoharness", ".venv", "node_modules", "__pycache__"))
        checks = tuple(EvalCheck(**item) for item in case["checks"])
        task = EvalTask(task_id, str(case["objective"]), checks)
        runtime = runtime_factory(workspace)
        state = runtime.create_run(task.objective, str(workspace))
        final = runtime.run(state.run_id)
        grade = evaluate_task(workspace, task, source=source, suite_dir=suite_file.parent)
        task_results.append({
            "task_id": task_id,
            "passed": grade.passed,
            "run_status": final.status.value,
            "steps": final.step,
            "tool_calls": final.tool_calls,
            "verification_runs": final.verification_runs,
            "rejected_completions": final.rejected_completions,
            "bypassed_rejections": final.bypassed_rejections,
            "error": final.error,
            "elapsed_seconds": final.elapsed_seconds,
            "planner_usage": final.planner_usage,
            "checks": grade.checks,
        })
        runtime.store.close()
    result = SuiteResult(suite_name, model, task_results, ablation)
    (output / "report.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
