# Hermes Contractor｜多多乙方实现

乙方应用，将多多（Hermes）接成 `contractor-duoduo` 身份。

## 职责

- 声明 contractor identity。
- 从公告板读取分配给自己的任务。
- 校验 `contractor_identity_id == contractor-duoduo`。
- `claim_task` 领取任务。
- `start_execution` 标记开始。
- 执行任务（调用 Hermes 执行器）。
- 写 `result_file`、`artifacts`、`execution_log`。
- `submit_result` 提交结果。
- 收到 `revision_requested` 后，围绕同一个 `task_id` 返工并 resubmit。
- 上下文不足时 `request_clarification` 或 `mark_blocked`。
- 不能替甲方验收。
- 不能关闭任务。
- 不能提交非自己分配的任务。

## 接口

```python
HermesContractor(root, identity_id, results_dir, logs_dir)
  .get_assigned_tasks()         -> list[dict]  # 扫描 board/tasks/active/ 过滤分配给自己的 task
  .claim_task(task_id)          -> dict        # 调用 lifecycle.claim_task
  .start_execution(task_id)     -> dict        # 调用 lifecycle.start_execution
  .execute_task(task_id, task_def) -> dict     # 调用 Hermes 执行
  .submit_result(task_id, result_file, artifacts, execution_log) -> dict
  .mark_blocked(task_id, reason) -> dict
  .request_clarification(task_id, question) -> dict
  .handle_revision(task_id)     -> dict        # 围绕 task_id 返工重做
```

## 限制

- 只处理 `contractor_identity_id == contractor-duoduo` 的任务。
- 不替甲方验收。
- 不关闭任务。
- 使用 `packages/board-core/agent_delegation_board/lifecycle.py` 的 lifecycle 函数，不走自定义状态机。
