# RepoHarness

RepoHarness is a small, inspectable Agent runtime for repository tasks. It focuses on the engineering layer around model tool calling: path-scoped repository tools, durable state, bounded execution, exactly-once mutations, event streaming and reproducible evaluation.

## Architecture

```text
OpenAI-compatible model / scripted evaluator
                    |
             function calls
                    v
      budgeted AgentRuntime loop
       |          |          |
   SQLite      tool-call    append-only
 checkpoint   idempotency     events
                    |
      repository tool registry
       |       |       |       |
    search   read   replace   tests
                    |
       MCP stdio / FastAPI + SSE
```

The standard-library runtime works without model credentials. `OpenAICompatiblePlanner` connects to any Chat Completions endpoint that supports tool calling. `ScriptedPlanner` makes failure injection and regression tests deterministic.

## Implemented capabilities

- Five schema-described repository tools: search, bounded read, optimistic exact replacement, bounded Python test execution, and change hashes.
- SQLite WAL persistence for checkpoints, append-only events and `(run_id, call_id)` tool-effect deduplication.
- Step, tool-call and wall-clock budgets; cancellation and explicit pause/resume states.
- MCP stdio server implementing initialization, tool discovery and tool execution.
- FastAPI transport with five endpoints and SSE event replay.
- Deterministic recovery benchmark and unit/integration tests requiring no external service.

## Run locally

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python benchmarks/run_benchmark.py
python -m repoharness.cli demo . --query TODO
```

Install the optional HTTP layer with `pip install -e ".[api]"`. Run a real model with an OpenAI-compatible endpoint:

```powershell
$env:OPENAI_API_KEY = "..."
repoharness run C:\path\to\repo "Locate the parsing bug, patch it, and run focused tests"
```

Start the MCP tool server:

```powershell
repoharness-mcp --workspace C:\path\to\repo
```

## Reliability model

Each side-effecting tool call has a stable `call_id`. The runtime writes its result before advancing the checkpoint. After interruption, the same call is served from SQLite rather than executed again. File edits add optimistic replacement-count checks and record before/after SHA-256 hashes. Subprocesses use argument arrays, an executable/module allowlist, a workspace working directory and hard timeouts.

This reduces accidental command injection but is not an OS security boundary: repository tests can execute arbitrary Python. Run untrusted repositories inside a container or VM with restricted mounts, network and resources.

The included benchmark measures only local runtime recovery. It intentionally excludes LLM quality and network latency; model-level task success should be evaluated on a fixed held-out task set with the model, prompt and budgets pinned.

