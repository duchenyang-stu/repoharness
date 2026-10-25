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

    def __post_init__(self) -> None:
        if self.max_steps < 1 or self.max_tool_calls < 1 or self.timeout_seconds <= 0:
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

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RunState":
        data = dict(raw)
        data["status"] = RunStatus(data["status"])
        return cls(**data)

