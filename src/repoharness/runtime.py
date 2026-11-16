"""Budgeted agent loop with durable checkpoints and replay-safe tool results."""

from __future__ import annotations

import json
import threading
import time
import uuid
from abc import ABC, abstractmethod

from .models import Ablation, Budget, PlannerTurn, RunState, RunStatus
from .context import compact_tool_result
from .store import SQLiteRunStore
from .tools import ToolRegistry


class Planner(ABC):
    @abstractmethod
    def next_turn(self, state: RunState, tool_schemas: list[dict]) -> PlannerTurn:
        raise NotImplementedError


class AgentRuntime:
    def __init__(
        self, store: SQLiteRunStore, tools: ToolRegistry, planner: Planner,
        budget: Budget | None = None, ablation: Ablation | None = None,
    ) -> None:
        self.store = store
        self.tools = tools
        self.planner = planner
        self.budget = budget or Budget()
        self.ablation = ablation or Ablation()
        self._cancelled: set[str] = set()
        self._cancel_lock = threading.Lock()

    def create_run(self, objective: str, workspace: str, *, run_id: str | None = None) -> RunState:
        if not objective.strip():
            raise ValueError("Objective cannot be empty")
        state = RunState(run_id=run_id or uuid.uuid4().hex, objective=objective, workspace=workspace)
        state.messages.append({"role": "user", "content": objective})
        self.store.save_state(state)
        self.store.append_event(state.run_id, "run.created", {"objective": objective, "workspace": workspace})
        return state

    def cancel(self, run_id: str) -> None:
        with self._cancel_lock:
            self._cancelled.add(run_id)
        state = self.store.load_state(run_id)
        if state.status not in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            state.status = RunStatus.CANCELLED
            self.store.save_state(state)
            self.store.append_event(run_id, "run.cancelled", {})

    def run(self, run_id: str, *, interrupt_after_tool_calls: int | None = None) -> RunState:
        state = self.store.load_state(run_id)
        if state.status in {RunStatus.SUCCEEDED, RunStatus.CANCELLED}:
            return state
        state.status = RunStatus.RUNNING
        state.started_monotonic = time.monotonic()
        self.store.save_state(state)
        self.store.append_event(run_id, "run.started", {"resumed": state.step > 0})
        try:
            while True:
                self._check_limits(state)
                turn = self.planner.next_turn(state, self.tools.schemas())
                state.step += 1
                self.store.append_event(run_id, "planner.completed", {
                    "step": state.step,
                    "tool_count": len(turn.calls),
                    "requested_completion": turn.final_answer is not None,
                    "usage": turn.usage,
                })
                for key, value in turn.usage.items():
                    if isinstance(value, int):
                        state.planner_usage[key] = state.planner_usage.get(key, 0) + value
                if turn.final_answer is not None:
                    rejection = self._completion_rejection(state)
                    if rejection and not self.ablation.completion_gate:
                        # Ablated: record what the gate would have done so its value can be measured.
                        state.bypassed_rejections += 1
                        self.store.append_event(run_id, "completion.gate_bypassed", {"reason": rejection})
                        rejection = None
                    if rejection:
                        state.rejected_completions += 1
                        state.messages.append({"role": "user", "content": rejection})
                        self.store.save_state(state)
                        self.store.append_event(run_id, "completion.rejected", {"reason": rejection})
                        continue
                    state.final_answer = turn.final_answer
                    state.messages.append({"role": "assistant", "content": turn.final_answer})
                    state.status = RunStatus.SUCCEEDED
                    self._finish_timing(state)
                    self.store.save_state(state)
                    self.store.append_event(run_id, "run.succeeded", {"answer": turn.final_answer, "steps": state.step})
                    return state

                state.messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call.call_id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments, ensure_ascii=False),
                            },
                        }
                        for call in turn.calls
                    ],
                })
                for call in turn.calls:
                    self._check_limits(state)
                    cached = self.store.cached_tool_result(run_id, call.call_id, call.name, call.arguments)
                    if cached is None:
                        self.store.append_event(run_id, "tool.started", {
                            "call_id": call.call_id, "name": call.name, "arguments": call.arguments,
                        })
                        tool = self.tools.get(call.name)
                        if tool.kind == "mutate" and not state.repository_inspected and self.ablation.read_before_write:
                            result = {
                                "ok": False,
                                "error": {
                                    "type": "PolicyError",
                                    "message": (
                                        "Inspect the repository with repo_overview before editing so the plan accounts "
                                        "for project instructions, language, manifests and tests."
                                    ),
                                },
                                "elapsed_ms": 0.0,
                            }
                        else:
                            result = tool.invoke(call.arguments)
                        self.store.save_tool_result(run_id, call.call_id, call.name, call.arguments, result)
                        state.tool_calls += 1
                        replayed = False
                    else:
                        result = cached
                        replayed = True
                    model_result = compact_tool_result(result) if self.ablation.compact_tool_results else result
                    state.messages.append({
                        "role": "tool", "tool_call_id": call.call_id, "name": call.name,
                        "content": model_result,
                    })
                    self.store.append_event(run_id, "tool.completed", {
                        "call_id": call.call_id, "name": call.name, "result": result, "replayed": replayed,
                    })
                    if not replayed:
                        self._record_evidence(state, call.name, result)
                    self._finish_timing(state)
                    self.store.save_state(state)
                    if interrupt_after_tool_calls is not None and state.tool_calls >= interrupt_after_tool_calls:
                        state.status = RunStatus.PAUSED
                        self.store.save_state(state)
                        self.store.append_event(run_id, "run.paused", {"reason": "injected_interrupt"})
                        return state
        except Exception as exc:
            state.status = RunStatus.FAILED
            state.error = f"{type(exc).__name__}: {exc}"
            self._finish_timing(state)
            self.store.save_state(state)
            self.store.append_event(run_id, "run.failed", {"error": state.error})
            return state

    def _record_evidence(self, state: RunState, tool_name: str, result: dict) -> None:
        if not result.get("ok"):
            return
        kind = self.tools.kind(tool_name)
        if kind == "overview":
            state.repository_inspected = True
        elif kind == "mutate":
            state.workspace_mutations += 1
            state.last_mutation_tool_call = state.tool_calls
            state.last_verification_passed = None
        elif kind == "verify":
            state.verification_runs += 1
            state.last_verification_tool_call = state.tool_calls
            data = result.get("data", {})
            state.last_verification_passed = bool(data.get("passed", data.get("returncode") == 0))

    @staticmethod
    def _completion_rejection(state: RunState) -> str | None:
        if state.workspace_mutations == 0:
            return None
        if state.last_verification_tool_call <= state.last_mutation_tool_call:
            return (
                "Completion rejected: the workspace changed after the latest verification. "
                "Run focused tests or checks, inspect their result, then provide the final answer with evidence."
            )
        if state.last_verification_passed is not True:
            return (
                "Completion rejected: the latest verification failed. Inspect the failure, repair the change, "
                "and run verification again before finishing."
            )
        return None

    def _check_limits(self, state: RunState) -> None:
        with self._cancel_lock:
            cancelled = state.run_id in self._cancelled
        if cancelled or self.store.load_state(state.run_id).status == RunStatus.CANCELLED:
            raise RuntimeError("Run was cancelled")
        if state.step >= self.budget.max_steps:
            raise RuntimeError("Step budget exceeded")
        if state.tool_calls >= self.budget.max_tool_calls:
            raise RuntimeError("Tool-call budget exceeded")
        elapsed = state.elapsed_seconds + (
            time.monotonic() - state.started_monotonic if state.started_monotonic is not None else 0.0
        )
        if elapsed >= self.budget.timeout_seconds:
            raise TimeoutError("Run timeout exceeded")

    @staticmethod
    def _finish_timing(state: RunState) -> None:
        if state.started_monotonic is not None:
            state.elapsed_seconds += time.monotonic() - state.started_monotonic
            state.started_monotonic = time.monotonic()

