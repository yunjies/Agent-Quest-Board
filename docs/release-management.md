# Agent委托公告板｜版本管理

本文定义 Agent 委托公告板的版本边界、兼容策略和发布门禁。

## 版本分层

本项目同时维护三类版本。

```text
board_protocol_version   协议版本：schema、状态机、权限语义、事件语义
framework_release        框架发布版本：仓库 release/tag，包含 SDK、adapter、app skeleton
implementation_version   组件实现版本：某个甲方/乙方/公告板实现自己的版本
```

### board_protocol_version

当前协议版本：

```text
1.0
```

只有以下变更才允许升级协议版本：

- 修改 `protocol/schemas/*` 的必填字段或字段语义。
- 修改状态机允许/禁止的流转。
- 修改 identity 权限语义。
- 修改事件类型语义。
- 修改 task lifecycle 的安全边界。

以下变更不升级协议版本：

- 新增 Lark、Hermes、Codex 等 adapter 实现。
- 新增 app 层实现。
- 新增测试、文档、示例配置。
- 修复 adapter 内部错误，但不改变协议字段。

### framework_release

框架发布版本使用 SemVer：

```text
0.1.0-local-baseline
0.2.0-formal-adapters
0.3.0-event-driven-loop
```

`0.x` 阶段表示产品仍在集成期，API 可调整，但每次调整必须记录 release manifest。

### implementation_version

每个组件单独声明实现版本：

```json
{
  "component_id": "contractor-duoduo",
  "component_type": "contractor",
  "implementation_version": "0.2.0",
  "board_protocol_version": "1.0",
  "supported_protocol_versions": ["1.0"]
}
```

公告板只按 `board_protocol_version` 和 capabilities 判断能否对接，不要求各组件实现版本完全一致。

## v1 兼容规则

同一任务中：

- principal identity 必须兼容当前 board protocol。
- contractor identity 必须兼容当前 board protocol。
- board identity 必须兼容当前 board protocol。
- principal 必须具备 `publish_task` 和 `review_task`。
- contractor 必须具备 `claim_task` 和 `submit_result`。
- board 必须具备 `append_event`、`transition_status`、`route_notification`。

不兼容时，公告板不得继续派单，必须写入：

```text
incompatible_component
```

或：

```text
needs_user_action
```

## 发布门禁

每个 release 必须通过：

```text
scripts/run-tests.ps1
apps/principal/codex-principal/run-smoke.ps1
apps/contractor/hermes-contractor/run-smoke.ps1
apps/board-interface/lark-topic-board/run-smoke.ps1
scripts/run-local-e2e.ps1
```

正式接入 release 额外要求：

- Hermes contractor 使用真实 ExecutionProvider，而不是默认占位执行器。
- Lark adapter 能在 dry-run 与真实发送失败场景下正确返回 success/failure。
- Lark 失败不会修改核心 task state。
- review-ready 后 Codex 可自动验收。
- rejected 后能回到原 contractor 返工。

## Release Manifest

每个 release 在 `protocol/releases/` 下保存一份 manifest：

```text
protocol/releases/{framework_release}.json
```

manifest 必须记录：

- framework_release
- board_protocol_version
- compatible_component_versions
- required_capabilities
- verification_commands
- known_limits

## 分支规则

```text
master
  稳定主干。只收已验收 release。

feature/codex-*
  Codex 甲方、协议、测试、release 管理开发。

feature/duoduo-contractor
  多多乙方/Hermes 接入。

feature/duoduo-board-interface
  多多公告板前端/Lark 接入。

integration/*
  临时联调分支。只由验收方合并，不作为日常开发分支。
```

## 当前 release 路线

```text
0.1.0-local-baseline
  本地 filesystem/no-real-Lark/no-real-Hermes 协议闭环。

0.2.0-formal-adapters
  接入真实 Hermes ExecutionProvider 与真实 Lark notifier 配置。

0.3.0-event-driven-loop
  接入 Principal Watcher、Board Dispatcher、Contractor Watcher，实现自动接单、自动验收、自动返工。
```
