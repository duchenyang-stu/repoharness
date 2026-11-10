# RepoHarness

RepoHarness 是一个面向真实代码仓库任务的 Coding Agent Harness 原型。项目重点是建立完整执行闭环：先理解仓库，再定位代码、校验并修改文件、审阅 Diff、运行验证，并用独立检查器判断任务是否真正完成。

## 核心闭环

```text
Task objective
      │
LLM Planner ── bounded context / tool schemas / usage
      │
Repository understanding
  repo_overview → instructions / languages / manifests / tests
      │
Evidence-driven execution
  search → bounded read → validated multi-file patch → unified diff
      │
Verification gate
  focused tests / lint / typecheck → completion allowed or rejected
      │
Independent task evaluator
  hidden repository-state checks → pass rate / steps / calls / tokens
```

## 已实现能力

### 1. 仓库上下文构建

- `repo_overview` 提取目录结构、语言扩展名、构建清单、仓库说明和测试布局。
- Runtime 在仓库概览完成前拒绝写操作，避免模型未读项目约束就直接修改代码。
- 搜索和读取均限制文件大小、结果数量及行范围；二进制文件、依赖目录和 Harness 状态目录不会进入上下文。

### 2. 补丁与工作区

- 支持精确单点替换和 `apply_patch` 多文件变更，可创建文件或同时修改多个文件。
- 所有替换都使用旧文本和预期次数做乐观校验；任一文件校验失败时，整批补丁不落盘。
- 所有变更在写入前统一校验；发生普通写入错误时回滚本批已写文件。该机制不宣称跨进程崩溃下的多文件原子性。
- `get_diff` 生成有大小上限的 unified diff，供模型在验证前审查最终变更。
- 文件通过临时文件和 `os.replace` 发布，避免写入半截内容。

### 3. 验证驱动的完成判定

- 支持 Python unittest / pytest / Ruff / MyPy，以及 npm、pnpm、yarn、Cargo 和 Go 的受限测试、Lint 或类型检查命令。
- 命令以参数数组执行，不经过 shell，并受工作区、可执行文件、子命令和超时限制。
- 一旦修改工作区，模型必须在最后一次修改后提供通过的验证结果；否则 Runtime 拒绝 final answer 并要求继续修复。
- `unittest` 返回 0 但实际运行 0 项测试时，不视为有效验证。

### 4. 上下文、状态与可观测性

- 工具大输出在进入模型历史前会压缩，完整结果仍保存在事件日志中；旧消息按确定性规则折叠，保留初始目标、近期证据和失败信号。
- SQLite WAL 保存 Run 状态、追加式事件和已提交的工具结果；相同调用标识在结果已提交后从缓存读取。
- 记录 Planner 步数、工具调用、验证次数、完成门禁拒绝次数、耗时及模型 token 用量。
- FastAPI + SSE 提供运行控制与事件流；MCP stdio 暴露同一套仓库工具。

### 5. 任务级评测

- `repoharness eval` 将每个任务复制到隔离工作区执行。
- 评测器不采信模型的完成声明，而是用隐藏的文件内容检查和测试命令评价最终仓库状态。
- 报告包含任务通过率、平均步骤、平均工具调用、验证次数、完成门禁拒绝次数、耗时和 token 用量。

## 运行测试

```powershell
$env:PYTHONPATH = "src"
.\.venv\bin\python.exe -m unittest discover -s tests -v
```

## 运行在线 Agent

在项目根目录或当前目录放一个 `.env`（参考 `.env.example`），启动时会自动读取；已在 shell 中设置的同名变量优先。`.env` 已被 `.gitignore` 忽略，不会被提交。

```powershell
copy .env.example .env   # 然后填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
repoharness run C:\path\to\repo "定位解析错误，修复代码并运行相关测试"
```

Planner 使用 OpenAI-compatible Chat Completions Tool Calling。Runtime 对具体模型供应商没有硬编码，但模型仍然承担仓库理解、证据选择、编辑规划和失败修复。

## 运行任务评测

```powershell
$env:OPENAI_API_KEY = "..."
repoharness eval evals\suite.json --output eval-results --model <model>
```

评测套件格式：

```json
{
  "name": "repo-fix-smoke",
  "tasks": [
    {
      "id": "fix-add",
      "workspace": "C:/fixtures/fix-add",
      "objective": "修复 add 的实现并运行测试",
      "checks": [
        {"kind": "file_contains", "path": "calc.py", "value": "a + b"},
        {"kind": "command", "command": ["python", "-m", "unittest", "discover"]}
      ]
    }
  ]
}
```

## 恢复语义与安全边界

工具结果提交到 SQLite 后，同一调用标识会直接返回已记录结果，避免恢复过程中再次执行。文件编辑同时使用旧内容校验和原子发布，重复或陈旧写入会被拒绝。当前实现没有把“文件副作用和 SQLite 结果”放入同一事务，因此不声称跨进程崩溃下的严格 exactly-once；生产级实现需要容器化工作区、写前日志或快照回滚来消除进程在写文件后、提交结果前退出的窗口。

路径与命令策略用于减少误操作，不构成操作系统安全边界。执行不受信任仓库时，应放入禁网、限资源、只挂载工作区的容器或虚拟机。

RepoHarness 当前仍是个人原型。它已经覆盖 Coding Agent 的核心执行闭环和任务级评测接口，但尚未达到成熟开源 Harness 在容器隔离、Git worktree、SWE-bench 适配、并发调度、人工审批和生产监控方面的完整度。
