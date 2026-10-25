"""Workspace path isolation and bounded subprocess execution."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence


class WorkspaceSandbox:
    BLOCKED_DIRS = {".git", ".hg", ".svn", ".repoharness", "node_modules", ".venv", "venv", "__pycache__"}

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError(f"Workspace is not a directory: {self.root}")

    def resolve(self, relative: str, *, must_exist: bool = False) -> Path:
        candidate = (self.root / relative).resolve(strict=False)
        try:
            relative_path = candidate.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError(f"Path escapes workspace: {relative}") from exc
        if any(part in self.BLOCKED_DIRS for part in relative_path.parts):
            raise PermissionError(f"Path is managed or excluded: {relative}")
        if must_exist and not candidate.exists():
            raise FileNotFoundError(relative)
        return candidate

    def source_files(self) -> list[Path]:
        files: list[Path] = []
        for directory, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [name for name in dirnames if name not in self.BLOCKED_DIRS]
            parent = Path(directory)
            for name in filenames:
                path = parent / name
                try:
                    if path.stat().st_size > 1_000_000:
                        continue
                    with path.open("rb") as stream:
                        if b"\x00" in stream.read(4096):
                            continue
                    files.append(path)
                except OSError:
                    continue
        return files

    def run(self, command: Sequence[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
        if not command:
            raise ValueError("Command cannot be empty")
        executable = Path(command[0]).name.lower()
        allowed = {"python", "python.exe", "py", "py.exe", "pytest", "pytest.exe"}
        if executable not in allowed:
            raise PermissionError(f"Executable is not allowed: {executable}")
        if executable in {"python", "python.exe", "py", "py.exe"}:
            if "-c" in command:
                raise PermissionError("Inline Python execution is not allowed")
            if "-m" in command:
                module_index = command.index("-m") + 1
                module = command[module_index] if module_index < len(command) else ""
                if module not in {"unittest", "pytest"}:
                    raise PermissionError(f"Python module is not allowed: {module}")
            elif len(command) > 1 and not command[1].startswith("-"):
                self.resolve(command[1], must_exist=True)
        return subprocess.run(
            list(command),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )

