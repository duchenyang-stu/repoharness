# 调度顺序

`Scheduler.add(name, run_at, priority=0)` 加入任务；`Scheduler.pop_due(now)` 取出**所有已到期**任务的名字列表，
并从调度器中移除它们。

- 到期条件：`run_at <= now`（恰好等于 `now` 也算到期）。
- 返回顺序：先按 `run_at` 从早到晚；`run_at` 相同时 `priority` **数值大的先执行**；
  `run_at` 与 `priority` 都相同时，**先加入的先执行**（FIFO），与名字无关。
- 同名任务允许重复加入，互相独立。
- `peek_time()` 返回下一个任务的 `run_at`，没有任务时返回 `None`。
- `len(scheduler)` 是尚未取出的任务数。
