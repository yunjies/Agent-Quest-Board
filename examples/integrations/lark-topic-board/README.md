# Lark Topic Board Example｜飞书话题公告板前端案例

这个案例展示飞书话题作为公告板前端的接入边界。

飞书不是事实源。飞书只展示任务、事件、通知和人工交互入口。事实源仍是公告板 task snapshot、event log 和 artifact index。

## 必须满足

- 每个 task 对应一个 topic ref。
- 同一 `task_id` 的日志集中在同一个 topic。
- reject 不关闭 topic。
- approve 后公告板 close，前端再标记关闭。
- Lark sync failed 写 incident，但不影响核心任务状态。

## 配置

使用 `config.example.yaml` 作为模板。真实 chat_id、topic_id、open_id、app secret 不能进入仓库。
