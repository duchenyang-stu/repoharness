"""Minimal .env loader so API settings need not be exported in every shell."""

from __future__ import annotations

import os
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key:
            values[key] = value
    return values


def load_env(search_dirs: list[Path] | None = None) -> list[Path]:
    """Load the first .env found, without overriding variables already set in the shell.

    Search order: current working directory, then the project root. Returns the loaded files.
    """
    candidates = search_dirs or [Path.cwd(), Path(__file__).resolve().parents[2]]
    loaded: list[Path] = []
    for directory in candidates:
        path = directory / ".env"
        if path in loaded or not path.is_file():
            continue
        for key, value in parse_env_file(path).items():
            os.environ.setdefault(key, value)
        loaded.append(path)
    return loaded
