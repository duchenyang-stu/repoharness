"""Bound model context while retaining recent evidence and failure signals."""

from __future__ import annotations

import json
from typing import Any


def compact_tool_result(result: dict[str, Any], max_chars: int = 10_000) -> dict[str, Any]:
    """Keep complete results in the event store and a bounded copy in model history."""
    encoded = json.dumps(result, ensure_ascii=False)
    if len(encoded) <= max_chars:
        return result
    summary: dict[str, Any] = {"ok": result.get("ok"), "truncated": True, "original_chars": len(encoded)}
    if result.get("ok"):
        data = result.get("data", {})
        summary["data_keys"] = sorted(data) if isinstance(data, dict) else []
        for key in ("path", "returncode", "truncated", "match_count", "modified_files", "summary"):
            if isinstance(data, dict) and key in data:
                summary[key] = data[key]
        for key in ("stdout", "stderr", "diff"):
            if isinstance(data, dict) and data.get(key):
                value = str(data[key])
                summary[key] = value[-3_000:]
    else:
        summary["error"] = result.get("error")
    return summary


def compact_messages(messages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """Preserve the objective and recent turns, summarize older tool traffic deterministically."""
    if not messages:
        return []
    serialized = [json.dumps(item, ensure_ascii=False) for item in messages]
    if sum(map(len, serialized)) <= max_chars:
        return list(messages)

    kept: list[dict[str, Any]] = []
    used = 0
    for message, raw in reversed(list(zip(messages, serialized))):
        if kept and used + len(raw) > int(max_chars * 0.72):
            break
        kept.append(message)
        used += len(raw)
    kept.reverse()
    start = len(messages) - len(kept)
    if start < len(messages) and messages[start].get("role") == "tool":
        for index in range(start - 1, -1, -1):
            candidate = messages[index]
            if candidate.get("role") == "assistant" and candidate.get("tool_calls"):
                start = index
                kept = messages[start:]
                break
    omitted = start
    failures = 0
    tools: list[str] = []
    for message in messages[:omitted]:
        if message.get("role") == "tool":
            tools.append(str(message.get("name", "unknown")))
            content = message.get("content", {})
            if isinstance(content, dict) and content.get("ok") is False:
                failures += 1
    summary = {
        "role": "system",
        "content": (
            f"Earlier context compacted: {omitted} messages, "
            f"{len(tools)} tool results, {failures} tool failures. "
            f"Tools used: {', '.join(tools[-20:]) or 'none'}."
        ),
    }
    first_user = next((m for m in messages if m.get("role") == "user"), None)
    prefix = [first_user] if first_user and first_user not in kept else []
    return prefix + [summary] + kept
