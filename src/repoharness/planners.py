"""Deterministic and OpenAI-compatible planners."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable
from typing import Any

from .models import PlannerTurn, RunState, ToolCall
from .runtime import Planner


class ScriptedPlanner(Planner):
    """Deterministic planner for demos, tests and reproducible evaluations."""

    def __init__(self, turns: Iterable[PlannerTurn]) -> None:
        self.turns = tuple(turns)

    def next_turn(self, state: RunState, tool_schemas: list[dict]) -> PlannerTurn:
        index = state.step
        if index >= len(self.turns):
            raise RuntimeError("Scripted planner has no remaining turn")
        return self.turns[index]


class OpenAICompatiblePlanner(Planner):
    """Small HTTP adapter for providers implementing Chat Completions tool calls."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 60.0) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def next_turn(self, state: RunState, tool_schemas: list[dict]) -> PlannerTurn:
        messages = [{"role": "system", "content": (
            "You are a repository engineering agent. Inspect before editing, use exact replacements, "
            "run focused tests, and finish with evidence."
        )}]
        for message in state.messages:
            if message["role"] == "tool":
                messages.append({
                    "role": "tool", "tool_call_id": message["tool_call_id"],
                    "content": json.dumps(message["content"], ensure_ascii=False),
                })
            else:
                messages.append(message)
        body = json.dumps({"model": self.model, "messages": messages, "tools": tool_schemas, "tool_choice": "auto"}).encode()
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload: dict[str, Any] = json.load(response)
        message = payload["choices"][0]["message"]
        calls = tuple(
            ToolCall(
                call_id=item["id"],
                name=item["function"]["name"],
                arguments=json.loads(item["function"]["arguments"]),
            )
            for item in message.get("tool_calls", [])
        )
        if calls:
            return PlannerTurn(calls=calls)
        return PlannerTurn(final_answer=message.get("content") or "Task completed without a textual summary.")

