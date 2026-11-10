"""SQLite persistence for runs, checkpoints, events and idempotent tool calls."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from .models import RunState, RunStatus


class SQLiteRunStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
                CREATE TABLE IF NOT EXISTS tool_calls (
                    run_id TEXT NOT NULL,
                    call_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_id, call_id)
                );
                """
            )

    def save_state(self, state: RunState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=False, separators=(",", ":"))
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO runs(run_id, status, state_json, updated_at)
                   VALUES(?, ?, ?, ?)
                   ON CONFLICT(run_id) DO UPDATE SET
                     status=excluded.status,
                     state_json=excluded.state_json,
                     updated_at=excluded.updated_at""",
                (state.run_id, state.status.value, payload, time.time()),
            )

    def load_state(self, run_id: str) -> RunState:
        with self._lock:
            row = self._connection.execute(
                "SELECT state_json FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown run: {run_id}")
        return RunState.from_dict(json.loads(row["state_json"]))

    def set_status(self, run_id: str, status: RunStatus) -> None:
        state = self.load_state(run_id)
        state.status = status
        self.save_state(state)

    def append_event(self, run_id: str, kind: str, payload: dict[str, Any]) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "INSERT INTO events(run_id, kind, payload_json, created_at) VALUES(?, ?, ?, ?)",
                (run_id, kind, json.dumps(payload, ensure_ascii=False), time.time()),
            )
            return int(cursor.lastrowid)

    def events(self, run_id: str, after: int = 0) -> Iterator[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT seq, kind, payload_json, created_at FROM events WHERE run_id = ? AND seq > ? ORDER BY seq",
                (run_id, after),
            ).fetchall()
        for row in rows:
            yield {
                "seq": row["seq"],
                "kind": row["kind"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }

    def cached_tool_result(
        self,
        run_id: str,
        call_id: str,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT tool_name, arguments_json, result_json FROM tool_calls WHERE run_id = ? AND call_id = ?",
                (run_id, call_id),
            ).fetchone()
        if row is None:
            return None
        if tool_name is not None and row["tool_name"] != tool_name:
            raise ValueError(f"Tool call id {call_id!r} was reused for a different tool")
        if arguments is not None:
            expected = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            actual = json.dumps(json.loads(row["arguments_json"]), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if actual != expected:
                raise ValueError(f"Tool call id {call_id!r} was reused with different arguments")
        return json.loads(row["result_json"])

    def save_tool_result(
        self,
        run_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO tool_calls
                   (run_id, call_id, tool_name, arguments_json, result_json, created_at)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    call_id,
                    tool_name,
                    json.dumps(arguments, ensure_ascii=False, sort_keys=True),
                    json.dumps(result, ensure_ascii=False),
                    time.time(),
                ),
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

