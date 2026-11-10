# RepoHarness Architecture

## Scope

RepoHarness 解决 Coding Agent 的执行与验证问题：把 LLM 的仓库任务决策转化为受约束工具调用，维护运行状态，要求修改后的验证证据，并独立评价最终仓库状态。它不实现基础模型，也不把工具协议、Web API 或内部测试数量当作任务能力指标。

## Control flow

```text
objective
   │
OpenAI-compatible Planner
   │ tool calls
AgentRuntime ── budgets / context compaction / completion gate
   │
ToolRegistry
   ├─ repository overview
   ├─ search and bounded read
   ├─ validated single or multi-file edits
   ├─ unified diff review
   └─ tests / lint / typecheck
   │
SQLite state + append-only events
   │
independent evaluation checks
```

## Correctness boundaries

- LLM 负责选择证据、规划修改和根据失败继续修复。
- Runtime 负责工具顺序策略、预算、状态、完成门禁与可观测数据。
- 工具负责路径约束、写前校验、单文件原子发布和受限命令执行。
- Evaluator 不采信模型文本，以最终文件状态和测试命令评分。
- 工具结果提交后的重复调用可以安全回放；文件写入和 SQLite 提交之间仍存在进程崩溃窗口。

## Remaining gaps to mature harnesses

| Area | Current state | Production-grade next step |
|---|---|---|
| Isolation | Path and command policy | Per-task container/VM, network and resource limits |
| Workspace | Directory copy in evals | Git worktree, clean patch export, rollback and merge conflict handling |
| Context | Text search, bounded reads, deterministic compaction | Symbol index, AST/LSP navigation, semantic retrieval and model-aware token budgets |
| Editing | Validated replace/create batches | Native patch parser, rename/delete, formatter integration and conflict recovery |
| Evaluation | JSON task suites and hidden checks | SWE-bench adapter, larger held-out suites and baseline comparisons |
| Governance | Automatic completion gate | Human approval for sensitive commands and policy tiers |
| Scheduling | One in-process run per worker | Durable queue, leases, concurrency and crash-safe workers |
| Observability | SQLite events, SSE and aggregate metrics | Trace backend, cost/latency dashboards and failure taxonomy |

The project should be described as a verification-gated Coding Agent Harness prototype until those gaps are addressed and evaluated on a representative held-out task set.
