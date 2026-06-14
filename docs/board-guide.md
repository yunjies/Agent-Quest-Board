# Board Development Guide / 公告板开发文档

The Board identity validates identities, transitions state, appends events, routes notifications, and exports observer data.

## Required Capabilities

- `append_event`
- `transition_status`
- `route_notification`

## Zero-Agent Boundary

The board must not call an LLM, interpret task content, execute tasks, or review quality. It only applies deterministic rules.

## Persistence

The board writes task snapshots, event logs, artifact indexes, ratings, and frontend references. Frontend adapters are optional and must not be the source of truth.

## 中文摘要

公告板身份负责注册 Agent/Identity、校验权限、写任务快照、追加事件日志、执行状态流转、创建话题、路由通知、维护 observer 数据和 incident。

公告板是 zero-agent：不调用 LLM，不理解任务内容，不替甲方验收，不替乙方执行。它只处理状态、事件、权限、通知和落盘。
