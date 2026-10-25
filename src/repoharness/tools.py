"""Structured repository tools exposed to models and MCP clients."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .sandbox import WorkspaceSandbox


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            payload = self.handler(arguments)
            return {"ok": True, "data": payload, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
        except Exception as exc:
            return {
                "ok": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            }

    def function_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.input_schema},
        }


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique")

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.function_schema() for tool in self._tools.values()]

    def mcp_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
            for tool in self._tools.values()
        ]


def _required(*names: str) -> dict[str, Any]:
    return {"type": "object", "required": list(names), "additionalProperties": False}


def build_repository_tools(workspace: str | Path) -> ToolRegistry:
    sandbox = WorkspaceSandbox(workspace)
    modified: dict[str, dict[str, str]] = {}

    def search_repo(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args["query"])
        limit = min(max(int(args.get("limit", 40)), 1), 200)
        use_regex = bool(args.get("regex", False))
        pattern = re.compile(query) if use_regex else None
        matches: list[dict[str, Any]] = []
        for path in sandbox.source_files():
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for index, line in enumerate(lines, 1):
                hit = bool(pattern.search(line)) if pattern else query.lower() in line.lower()
                if hit:
                    matches.append({"path": str(path.relative_to(sandbox.root)), "line": index, "text": line[:500]})
                    if len(matches) >= limit:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def read_file(args: dict[str, Any]) -> dict[str, Any]:
        path = sandbox.resolve(str(args["path"]), must_exist=True)
        if not path.is_file():
            raise ValueError("Path is not a file")
        start = max(int(args.get("start_line", 1)), 1)
        end = min(int(args.get("end_line", start + 199)), start + 499)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = [{"line": n, "text": lines[n - 1]} for n in range(start, min(end, len(lines)) + 1)]
        return {"path": str(path.relative_to(sandbox.root)), "total_lines": len(lines), "lines": selected}

    def replace_text(args: dict[str, Any]) -> dict[str, Any]:
        path = sandbox.resolve(str(args["path"]), must_exist=True)
        old = str(args["old"])
        new = str(args["new"])
        expected = int(args.get("expected_replacements", 1))
        if not old:
            raise ValueError("old cannot be empty")
        content = path.read_text(encoding="utf-8")
        count = content.count(old)
        if count != expected:
            raise ValueError(f"Expected {expected} replacement(s), found {count}")
        updated = content.replace(old, new)
        before_hash = hashlib.sha256(content.encode()).hexdigest()
        after_hash = hashlib.sha256(updated.encode()).hexdigest()
        path.write_text(updated, encoding="utf-8")
        relative = str(path.relative_to(sandbox.root))
        modified[relative] = {"before_sha256": before_hash, "after_sha256": after_hash}
        return {"path": relative, "replacements": count, **modified[relative]}

    def run_tests(args: dict[str, Any]) -> dict[str, Any]:
        command = args.get("command", ["python", "-m", "unittest", "discover"])
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("command must be a string array")
        timeout = min(max(float(args.get("timeout_seconds", 60)), 0.1), 300.0)
        completed = sandbox.run(command, timeout)
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20_000:],
            "stderr": completed.stderr[-20_000:],
        }

    def get_changes(_: dict[str, Any]) -> dict[str, Any]:
        return {"modified_files": [{"path": path, **hashes} for path, hashes in sorted(modified.items())]}

    object_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    return ToolRegistry([
        Tool("search_repo", "Search text or a regular expression in repository files.", {
            **_required("query"), "properties": {"query": {"type": "string"}, "regex": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 200}}
        }, search_repo),
        Tool("read_file", "Read a bounded line range from a UTF-8 repository file.", {
            **_required("path"), "properties": {"path": {"type": "string"}, "start_line": {"type": "integer", "minimum": 1}, "end_line": {"type": "integer", "minimum": 1}}
        }, read_file),
        Tool("replace_text", "Replace an exact string with optimistic replacement-count validation.", {
            **_required("path", "old", "new"), "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "expected_replacements": {"type": "integer", "minimum": 1}}
        }, replace_text),
        Tool("run_tests", "Run a bounded Python unittest or pytest command without a shell.", {
            "type": "object", "properties": {"command": {"type": "array", "items": {"type": "string"}}, "timeout_seconds": {"type": "number", "minimum": 0.1, "maximum": 300}}, "additionalProperties": False
        }, run_tests),
        Tool("get_changes", "List files modified by repository tools with before/after SHA-256 hashes.", object_schema, get_changes),
    ])

