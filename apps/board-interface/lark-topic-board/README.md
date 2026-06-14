# Lark Topic Board｜飞书话题公告板前端 Interface

飞书话题公告板前端，负责把公告板任务事件路由到飞书话题。

## 职责

- 每个 task_id 对应一个飞书话题。
- 同一个 task_id 的所有消息进入同一个话题。
- 发布任务时通知乙方。
- result_submitted 时通知甲方验收。
- reject 时通知原 contractor 返工。
- approved + closed 后标记话题关闭。
- Lark sync failed 时写 incident，但不影响核心 task 状态。

## 不是

- ✗ 不调用 LLM。
- ✗ 不理解任务内容。
- ✗ 不替甲方验收。
- ✗ 不替乙方执行。
- ✗ 不是事实源（飞书只做前端展示）。
- ✗ 不直接修改 board 状态机。

## 事件 → 通知路由

| 事件 | 通知对象 | 动作 |
|------|---------|------|
| task_published | contractor | 创建话题，通知领取 |
| result_submitted | principal | 通知验收 |
| review_rejected | contractor | 通知返工 |
| review_approved | both | 准备关闭话题 |
| task_closed | both | 关闭话题 |
| incident_created | operator | 通知异常 |
