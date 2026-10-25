from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from repoharness.api import create_app
from repoharness.models import PlannerTurn, ToolCall
from repoharness.planners import ScriptedPlanner
from repoharness.runtime import AgentRuntime
from repoharness.store import SQLiteRunStore
from repoharness.tools import build_repository_tools


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sample.py").write_text("# TODO: verify API\n", encoding="utf-8")
        self.stores: list[SQLiteRunStore] = []

        def runtime_factory(workspace: str) -> AgentRuntime:
            store = SQLiteRunStore(self.root / f"runs-{len(self.stores)}.db")
            self.stores.append(store)
            planner = ScriptedPlanner([
                PlannerTurn(calls=(ToolCall("api-search", "search_repo", {"query": "TODO"}),)),
                PlannerTurn(final_answer="API task complete"),
            ])
            return AgentRuntime(store, build_repository_tools(workspace), planner)

        self.client = TestClient(create_app(runtime_factory))

    def tearDown(self) -> None:
        for store in self.stores:
            store.close()
        self.temp.cleanup()

    def test_create_get_and_stream_run(self):
        created = self.client.post("/runs", json={"objective": "inspect TODO", "workspace": str(self.root)})
        self.assertEqual(created.status_code, 202)
        run_id = created.json()["run_id"]
        state = None
        for _ in range(100):
            response = self.client.get(f"/runs/{run_id}")
            state = response.json()
            if state["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["final_answer"], "API task complete")
        events = self.client.get(f"/runs/{run_id}/events")
        self.assertEqual(events.status_code, 200)
        self.assertIn("event: run.succeeded", events.text)

    def test_validation_and_unknown_run(self):
        invalid = self.client.post("/runs", json={"objective": "", "workspace": str(self.root)})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(self.client.get("/runs/missing").status_code, 404)

    def test_expected_run_routes_exist(self):
        paths = {route.path for route in self.client.app.routes}
        self.assertTrue({
            "/runs", "/runs/{run_id}", "/runs/{run_id}/resume",
            "/runs/{run_id}/cancel", "/runs/{run_id}/events",
        }.issubset(paths))


if __name__ == "__main__":
    unittest.main()
