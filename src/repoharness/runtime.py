"""Budgeted agent loop with durable checkpoints and exactly-once tool effects."""

from __future__ import annotations

import json
import threading
import time
import uuid
from abc import ABC, abstractmethod

from .models import Budget, PlannerTurn, RunState, RunStatus
from .store import SQLiteRunStore
from .tools import ToolRegistry


class Planner(ABC):
    @abstractmethod
    def next_turn(self, state: RunState, tool_schemas: list[dict]) -> PlannerTurn:
        raise NotImplementedError


class AgentRuntime:
    def __init__(self, store: SQLiteRunStore, tools: ToolRegistry, planner: Planner, budget: Budget | None = None) -> None:
        self.store = store
        self.tools = tools
        self.planner = planner
        self.budget = budget or Budget()
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
                if turn.final_answer is not None:
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
                    cached = self.store.cached_tool_result(run_id, call.call_id)
                    if cached is None:
                        result = self.tools.get(call.name).invoke(call.arguments)
                        self.store.save_tool_result(run_id, call.call_id, call.name, call.arguments, result)
                        state.tool_calls += 1
                        replayed = False
                    else:
                        result = cached
                        replayed = True
                    state.messages.append({
                        "role": "tool", "tool_call_id": call.call_id, "name": call.name,
                        "content": result,
                    })
                    self.store.append_event(run_id, "tool.completed", {
                        "call_id": call.call_id, "name": call.name, "result": result, "replayed": replayed,
                    })
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

