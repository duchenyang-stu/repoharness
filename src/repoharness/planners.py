"""Deterministic and OpenAI-compatible planners."""

from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any

from .models import PlannerTurn, RunState, ToolCall
from .runtime import Planner
from .context import compact_messages


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

    def __init__(
        self, base_url: str, api_key: str, model: str, timeout_seconds: float = 60.0,
        max_context_chars: int = 48_000, compact_context: bool = True,
        max_retries: int = 3, retry_backoff_seconds: float = 2.0, temperature: float | None = None,
    ) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_context_chars = max_context_chars
        self.compact_context = compact_context
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.retries_used = 0
        self.temperature = temperature

    def next_turn(self, state: RunState, tool_schemas: list[dict]) -> PlannerTurn:
        messages = [{"role": "system", "content": (
            "You are a repository engineering agent. Start with repo_overview, read repository instructions, "
            "inspect relevant code before editing, prefer validated multi-file patches, review the diff, "
            "run focused tests or checks after the final edit, and finish with concrete evidence."
        )}]
        history = compact_messages(state.messages, self.max_context_chars) if self.compact_context else state.messages
        for message in history:
            if message["role"] == "tool":
                messages.append({
                    "role": "tool", "tool_call_id": message["tool_call_id"],
                    "content": json.dumps(message["content"], ensure_ascii=False),
                })
            else:
                messages.append(message)
        request_body: dict[str, Any] = {"model": self.model, "messages": messages, "tools": tool_schemas, "tool_choice": "auto"}
        if self.temperature is not None:
            request_body["temperature"] = self.temperature
        body = json.dumps(request_body).encode()
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        payload = self._post(request)
        message = payload["choices"][0]["message"]
        calls = tuple(
            ToolCall(
                call_id=item["id"],
                name=item["function"]["name"],
                arguments=json.loads(item["function"]["arguments"]),
            )
            for item in message.get("tool_calls", [])
        )
        usage = payload.get("usage") or {}
        if calls:
            return PlannerTurn(calls=calls, usage=usage)
        return PlannerTurn(final_answer=message.get("content") or "Task completed without a textual summary.", usage=usage)


    _TRANSIENT_HTTP = frozenset({408, 429, 500, 502, 503, 504})

    def _post(self, request: urllib.request.Request) -> dict[str, Any]:
        """POST with bounded retry on transient network/server errors (the same for every ablation arm)."""
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                transient = exc.code in self._TRANSIENT_HTTP
                error: Exception = exc
            except (urllib.error.URLError, ssl.SSLError, socket.timeout, ConnectionError, TimeoutError) as exc:
                transient = True
                error = exc
            if not transient or attempt >= self.max_retries:
                raise error
            attempt += 1
            self.retries_used += 1
            time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))
