"""Serializable domain models for the harness runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Budget:
    max_steps: int = 20
    max_tool_calls: int = 40
    timeout_seconds: float = 300.0
    max_context_chars: int = 48_000

    def __post_init__(self) -> None:
        if self.max_steps < 1 or self.max_tool_calls < 1 or self.timeout_seconds <= 0 or self.max_context_chars < 2_000:
            raise ValueError("Budget values must be positive")


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class PlannerTurn:
    calls: tuple[ToolCall, ...] = ()
    final_answer: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if bool(self.calls) == bool(self.final_answer is not None):
            raise ValueError("A planner turn must contain either tool calls or a final answer")


@dataclass
class RunState:
    run_id: str
    objective: str
    workspace: str
    status: RunStatus = RunStatus.QUEUED
    step: int = 0
    tool_calls: int = 0
    started_monotonic: float | None = None
    elapsed_seconds: float = 0.0
    messages: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str | None = None
    error: str | None = None
    workspace_mutations: int = 0
    verification_runs: int = 0
    last_mutation_tool_call: int = -1
    last_verification_tool_call: int = -1
    last_verification_passed: bool | None = None
    rejected_completions: int = 0
    planner_usage: dict[str, int] = field(default_factory=dict)
    repository_inspected: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RunState":
        data = dict(raw)
        data["status"] = RunStatus(data["status"])
        legacy_mutation_step = data.pop("last_mutation_step", None)
        legacy_verification_step = data.pop("last_verification_step", None)
        if "last_mutation_tool_call" not in data and legacy_mutation_step is not None:
            data["last_mutation_tool_call"] = int(data.get("tool_calls", -1)) if legacy_mutation_step >= 0 else -1
        if "last_verification_tool_call" not in data and legacy_verification_step is not None:
            data["last_verification_tool_call"] = int(data.get("tool_calls", -1)) if legacy_verification_step >= 0 else -1
        return cls(**data)

