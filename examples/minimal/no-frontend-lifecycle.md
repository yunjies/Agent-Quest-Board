# No-Frontend Lifecycle｜无前端生命周期

最小闭环：

```text
principal publish_task
board append task_published
contractor claim_task
contractor start_execution
contractor submit_result
board request_review
principal approve_task
board close_task
```

验收点：

- active task 在发布后存在。
- event log 是 append-only JSONL。
- result_file 写入 task snapshot。
- review_file 写入 task snapshot。
- 只有 approved 后才能 close。
- close 后 task 从 `tasks/active` 移到 `tasks/closed`。
