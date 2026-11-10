"""FastAPI transport for running and observing repository agents."""

import json
import threading
import time
from collections.abc import Callable
from typing import Any

from .models import RunStatus
from .runtime import AgentRuntime


def create_app(runtime_factory: Callable[[str], AgentRuntime]):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import StreamingResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Install RepoHarness with the 'api' extra to use FastAPI") from exc

    class CreateRunRequest(BaseModel):
        objective: str = Field(min_length=1, max_length=10_000)
        workspace: str = Field(min_length=1)

    app = FastAPI(title="RepoHarness", version="0.2.0")
    runtimes: dict[str, AgentRuntime] = {}
    lock = threading.Lock()

    def lookup(run_id: str) -> AgentRuntime:
        with lock:
            runtime = runtimes.get(run_id)
        if runtime is None:
            raise HTTPException(status_code=404, detail="run not found")
        return runtime

    @app.post("/runs", status_code=202)
    def create_run(request: CreateRunRequest) -> dict[str, Any]:
        runtime = runtime_factory(request.workspace)
        state = runtime.create_run(request.objective, request.workspace)
        with lock:
            runtimes[state.run_id] = runtime
        threading.Thread(target=runtime.run, args=(state.run_id,), daemon=True).start()
        return {"run_id": state.run_id, "status": state.status.value}

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        return lookup(run_id).store.load_state(run_id).to_dict()

    @app.post("/runs/{run_id}/resume", status_code=202)
    def resume_run(run_id: str) -> dict[str, Any]:
        runtime = lookup(run_id)
        state = runtime.store.load_state(run_id)
        if state.status not in {RunStatus.PAUSED, RunStatus.FAILED}:
            raise HTTPException(status_code=409, detail=f"run cannot resume from {state.status.value}")
        state.error = None
        runtime.store.save_state(state)
        threading.Thread(target=runtime.run, args=(run_id,), daemon=True).start()
        return {"run_id": run_id, "status": "running"}

    @app.post("/runs/{run_id}/cancel", status_code=202)
    def cancel_run(run_id: str) -> dict[str, Any]:
        runtime = lookup(run_id)
        runtime.cancel(run_id)
        return {"run_id": run_id, "status": "cancelled"}

    @app.get("/runs/{run_id}/events")
    def stream_events(run_id: str, after: int = 0):
        runtime = lookup(run_id)

        def generate():
            cursor = after
            while True:
                events = list(runtime.store.events(run_id, cursor))
                for event in events:
                    cursor = event["seq"]
                    yield f"id: {cursor}\nevent: {event['kind']}\ndata: {json.dumps(event['payload'], ensure_ascii=False)}\n\n"
                status = runtime.store.load_state(run_id).status
                if status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED} and not events:
                    break
                time.sleep(0.05)

        return StreamingResponse(generate(), media_type="text/event-stream")

    return app

