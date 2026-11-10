"""Structured repository tools exposed to models and MCP clients."""

from __future__ import annotations

import hashlib
import difflib
import os
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
    kind: str = "inspect"

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            self._validate(arguments)
            payload = self.handler(arguments)
            return {"ok": True, "data": payload, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
        except Exception as exc:
            return {
                "ok": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            }

    def _validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        required = self.input_schema.get("required", [])
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ValueError(f"Missing required argument(s): {', '.join(missing)}")
        properties = self.input_schema.get("properties", {})
        if self.input_schema.get("additionalProperties") is False:
            unknown = sorted(set(arguments) - set(properties))
            if unknown:
                raise ValueError(f"Unknown argument(s): {', '.join(unknown)}")

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

    def kind(self, name: str) -> str:
        return self.get(name).kind

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
    originals: dict[str, str | None] = {}

    def relative_path(path: Path) -> str:
        return path.relative_to(sandbox.root).as_posix()

    def remember_original(path: Path) -> None:
        relative = relative_path(path)
        if relative not in originals:
            originals[relative] = path.read_text(encoding="utf-8") if path.exists() else None

    def write_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".repoharness.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    def repo_overview(args: dict[str, Any]) -> dict[str, Any]:
        max_files = min(max(int(args.get("max_files", 200)), 20), 500)
        files = sorted(sandbox.source_files(), key=lambda item: relative_path(item).lower())
        extension_counts: dict[str, int] = {}
        paths: list[str] = []
        tests: list[str] = []
        instructions: list[str] = []
        manifests: list[str] = []
        manifest_names = {
            "pyproject.toml", "requirements.txt", "package.json", "pnpm-lock.yaml", "yarn.lock",
            "cargo.toml", "go.mod", "pom.xml", "build.gradle", "cmakelists.txt",
        }
        instruction_names = {"agents.md", "contributing.md", "readme.md"}
        for path in files:
            relative = relative_path(path)
            suffix = path.suffix.lower() or "<none>"
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            lower_name = path.name.lower()
            if lower_name in manifest_names:
                manifests.append(relative)
            if lower_name in instruction_names:
                instructions.append(relative)
            if lower_name.startswith("test_") or lower_name.endswith("_test.py") or "/tests/" in f"/{relative.lower()}/":
                tests.append(relative)
            if len(paths) < max_files:
                paths.append(relative)
        top_directories = sorted({path.split("/", 1)[0] for path in paths if "/" in path})
        return {
            "file_count": len(files),
            "tree": paths,
            "tree_truncated": len(files) > max_files,
            "top_directories": top_directories[:50],
            "language_extensions": sorted(extension_counts.items(), key=lambda item: (-item[1], item[0]))[:20],
            "manifests": manifests[:30],
            "instruction_files": instructions[:30],
            "test_files": tests[:60],
        }

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
                    matches.append({"path": relative_path(path), "line": index, "text": line[:500]})
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
        return {"path": relative_path(path), "total_lines": len(lines), "lines": selected}

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
        remember_original(path)
        write_atomic(path, updated)
        relative = relative_path(path)
        modified[relative] = {"before_sha256": before_hash, "after_sha256": after_hash}
        return {"path": relative, "replacements": count, **modified[relative]}

    def apply_patch(args: dict[str, Any]) -> dict[str, Any]:
        changes = args.get("changes")
        if not isinstance(changes, list) or not changes:
            raise ValueError("changes must be a non-empty array")
        if len(changes) > 20:
            raise ValueError("A patch may touch at most 20 files")
        prepared: dict[Path, str] = {}
        metadata: list[dict[str, Any]] = []
        seen: set[Path] = set()
        for change in changes:
            if not isinstance(change, dict):
                raise ValueError("Each change must be an object")
            operation = str(change.get("operation", "replace"))
            path = sandbox.resolve(str(change.get("path", "")), must_exist=operation == "replace")
            if path in seen:
                raise ValueError("Each file may appear once per patch batch")
            seen.add(path)
            if operation == "create":
                if path.exists():
                    raise ValueError(f"Cannot create existing file: {change.get('path')}")
                updated = str(change.get("content", ""))
                before = None
                replacements = 0
            elif operation == "replace":
                if not path.is_file():
                    raise ValueError(f"Path is not a file: {change.get('path')}")
                before = path.read_text(encoding="utf-8")
                old = str(change.get("old", ""))
                new = str(change.get("new", ""))
                expected = int(change.get("expected_replacements", 1))
                if not old:
                    raise ValueError("old cannot be empty for replace operations")
                replacements = before.count(old)
                if replacements != expected:
                    raise ValueError(f"Expected {expected} replacement(s) in {change.get('path')}, found {replacements}")
                updated = before.replace(old, new)
            else:
                raise ValueError(f"Unsupported patch operation: {operation}")
            if len(updated.encode("utf-8")) > 2_000_000:
                raise ValueError(f"Patched file is too large: {change.get('path')}")
            prepared[path] = updated
            metadata.append({"path": relative_path(path), "operation": operation, "replacements": replacements})

        applied: list[Path] = []
        backups = {path: (path.read_text(encoding="utf-8") if path.exists() else None) for path in prepared}
        try:
            for path, updated in prepared.items():
                remember_original(path)
                write_atomic(path, updated)
                applied.append(path)
                relative = relative_path(path)
                before = backups[path] or ""
                modified[relative] = {
                    "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
                    "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
                }
        except Exception:
            for path in reversed(applied):
                original = backups[path]
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    write_atomic(path, original)
            raise
        return {"validated_before_write": True, "rollback_on_write_error": True, "changed_files": metadata}

    def run_tests(args: dict[str, Any]) -> dict[str, Any]:
        command = args.get("command", ["python", "-m", "unittest", "discover"])
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("command must be a string array")
        timeout = min(max(float(args.get("timeout_seconds", 60)), 0.1), 300.0)
        completed = sandbox.run(command, timeout)
        combined_output = completed.stdout + "\n" + completed.stderr
        unittest_without_tests = (
            any(item == "unittest" for item in command)
            and re.search(r"Ran\s+0\s+tests?", combined_output, flags=re.IGNORECASE) is not None
        )
        passed = completed.returncode == 0 and not unittest_without_tests
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20_000:],
            "stderr": completed.stderr[-20_000:],
            "passed": passed,
            "zero_tests_detected": unittest_without_tests,
        }

    def get_changes(_: dict[str, Any]) -> dict[str, Any]:
        return {"modified_files": [{"path": path, **hashes} for path, hashes in sorted(modified.items())]}

    def get_diff(args: dict[str, Any]) -> dict[str, Any]:
        max_chars = min(max(int(args.get("max_chars", 20_000)), 1_000), 60_000)
        chunks: list[str] = []
        for relative, original in sorted(originals.items()):
            path = sandbox.resolve(relative)
            current = path.read_text(encoding="utf-8") if path.exists() else None
            before_lines = [] if original is None else original.splitlines(keepends=True)
            after_lines = [] if current is None else current.splitlines(keepends=True)
            chunks.extend(difflib.unified_diff(
                before_lines, after_lines,
                fromfile=f"a/{relative}" if original is not None else "/dev/null",
                tofile=f"b/{relative}" if current is not None else "/dev/null",
            ))
        diff = "".join(chunks)
        return {
            "diff": diff[:max_chars],
            "truncated": len(diff) > max_chars,
            "changed_file_count": len(originals),
            "diff_chars": len(diff),
        }

    object_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    return ToolRegistry([
        Tool("repo_overview", "Inspect repository structure, languages, manifests, instructions and tests before planning edits.", {
            "type": "object", "properties": {"max_files": {"type": "integer", "minimum": 20, "maximum": 500}}, "additionalProperties": False
        }, repo_overview, kind="overview"),
        Tool("search_repo", "Search text or a regular expression in repository files.", {
            **_required("query"), "properties": {"query": {"type": "string"}, "regex": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 200}}
        }, search_repo),
        Tool("read_file", "Read a bounded line range from a UTF-8 repository file.", {
            **_required("path"), "properties": {"path": {"type": "string"}, "start_line": {"type": "integer", "minimum": 1}, "end_line": {"type": "integer", "minimum": 1}}
        }, read_file),
        Tool("replace_text", "Replace an exact string with optimistic replacement-count validation.", {
            **_required("path", "old", "new"), "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "expected_replacements": {"type": "integer", "minimum": 1}}
        }, replace_text, kind="mutate"),
        Tool("apply_patch", "Create or edit multiple files after validating every change; roll back completed writes on error.", {
            **_required("changes"),
            "properties": {"changes": {"type": "array", "minItems": 1, "maxItems": 20, "items": {
                "type": "object", "required": ["path", "operation"], "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"}, "operation": {"type": "string", "enum": ["create", "replace"]},
                    "old": {"type": "string"}, "new": {"type": "string"}, "content": {"type": "string"},
                    "expected_replacements": {"type": "integer", "minimum": 1}
                }
            }}}
        }, apply_patch, kind="mutate"),
        Tool("run_tests", "Run bounded repository checks without a shell and return explicit pass/fail evidence.", {
            "type": "object", "properties": {"command": {"type": "array", "items": {"type": "string"}}, "timeout_seconds": {"type": "number", "minimum": 0.1, "maximum": 300}}, "additionalProperties": False
        }, run_tests, kind="verify"),
        Tool("get_changes", "List files modified by repository tools with before/after SHA-256 hashes.", object_schema, get_changes),
        Tool("get_diff", "Review a bounded unified diff of all changes made during the run.", {
            "type": "object", "properties": {"max_chars": {"type": "integer", "minimum": 1000, "maximum": 60000}}, "additionalProperties": False
        }, get_diff),
    ])

