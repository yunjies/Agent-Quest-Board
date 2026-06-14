# Integration Testing / 联调方案

## Normal Approve Path

1. Principal publishes a high-score task.
2. Board persists task snapshot and event log.
3. Contractor claims and executes.
4. Contractor submits a result file.
5. Board marks the task submitted and requests principal review.
6. Principal approves.
7. Board closes the task.

Expected result: task status is `closed`, event chain is complete, and result/review artifacts exist.

## Rejection and Revision Path

1. Principal publishes a medium-score task.
2. Contractor submits insufficient evidence.
3. Principal rejects with actionable feedback.
4. Board marks `revision_requested`.
5. Contractor revises and resubmits.
6. Principal approves.
7. Board closes the task.

Expected result: the same task ID is reused and the topic is not closed before approval.

## No-Frontend Mode

Disable frontend adapters and run the same lifecycle through filesystem persistence only. Core task state must remain complete.

## 中文摘要

联调目标是验证三方独立开发后能在同一协议下完成闭环：

```text
甲方发布 -> 公告板登记/建话题 -> 乙方执行 -> 公告板通知验收 -> 甲方验收 -> 公告板关闭或派回
```

必须覆盖正常通过、驳回返工、权限隔离、无飞书运行、异常与恢复五类用例。
