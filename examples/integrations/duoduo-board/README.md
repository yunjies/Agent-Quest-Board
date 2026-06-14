# Duoduo Board Example｜多多公告板承载案例

这个案例展示多多作为 `board-duoduo` 承载公告板运行时的接入边界。

多多可以同时拥有 contractor identity 和 board identity，但必须隔离：

```text
contractor-duoduo  可以执行任务
board-duoduo       只能处理状态、权限、事件、通知、落盘
```

## 必须对齐

- 状态机使用 `packages/board-core`。
- 事件日志使用 `{task_id}.jsonl`。
- reject 后派回原 contractor。
- approve 后才 close。
- frontend failure 不影响核心状态。
