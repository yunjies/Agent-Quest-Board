# Lark Topic Board｜飞书话题公告板前端 Interface Skeleton

飞书话题公告板前端 skeleton，负责把公告板任务事件翻译为前端通知结构体。

## 当前状态：前端 interface skeleton

这是 Lark 公告板前端的 **interface skeleton**，不是完整 Lark adapter。

**已实现：**
- 根据 event 生成 notification dict（6 种事件路由）
- 维护 `task_id` → `topic_id` 映射（文件持久化）
- 话题生命周期管理：assign → active → close
- 事件 → 通知消息模板（固定模板，不调用 LLM）
- Batch processing（批量事件处理）

**未实现（需在 `adapters/lark/` 中补全）：**
- 真实飞书 API 调用（创建话题、发送消息）
- 飞书话题组管理
- Lark token 认证和刷新
- 从飞书话题读取反馈

## 事件 → 通知路由

| 事件 | 通知对象 | 动作 |
|------|---------|------|
| task_published | contractor | 创建话题，通知领取 |
| result_submitted | principal | 通知验收 |
| review_rejected | contractor | 通知返工 |
| review_approved | both | 准备关闭话题 |
| task_closed | both | 关闭话题 |
| incident_created | operator | 通知异常 |

## Zero-agent 边界

- 不调用 LLM。
- 不理解任务内容。
- 不替甲方验收。
- 不替乙方执行。
- 不直接修改 board 状态机。
- 飞书只是前端，不是事实源。
- Lark sync 失败写 incident，不影响核心状态。

## 飞书通知对接

真实飞书 API 调用（话题创建、消息发送、话题关闭）后续应在 `adapters/lark/` 中实现。
本模块输出通知结构体 `dict`，由 Lark adapter 消费后调用飞书 API。
