# Agent委托公告板｜正式接入计划

本文定义从本地协议闭环进入正式 Hermes/Lark 接入的执行计划。

## 当前已通过基线

当前已通过：

```text
framework_release: 0.1.0-local-baseline
board_protocol_version: 1.0
```

能力范围：

- Codex principal 可发布、验收、关闭本地任务。
- Hermes contractor app 有可插拔 `ExecutionProvider`。
- Lark topic board interface 能生成通知结构。
- Lark notifier 已能正确表达发送成功/失败。
- filesystem board runtime 可作为事实源完成本地闭环。

限制：

- contractor 默认执行器仍是占位实现。
- Lark notifier 尚未接入真实运行配置与话题组。
- 自动接单、自动验收、自动返工 watcher 尚未形成产品级闭环。

## 目标 release

```text
framework_release: 0.2.0-formal-adapters
board_protocol_version: 1.0
```

协议版本保持 `1.0`，因为正式接入只补 adapter/app 实现，不改变 schema、状态机或权限语义。

## 工作包 A：真实 Hermes ExecutionProvider

负责方：多多

分支：

```text
feature/duoduo-contractor
```

目标：

- 新增真实 Hermes execution provider。
- `HermesContractor.execute_task()` 可通过配置选择 provider。
- provider 输出仍符合协议：
  - `result_file`
  - `artifacts`
  - `execution_log`
- 执行失败时不得伪造成功结果，必须写入 blocked/failed/needs_user_action。
- contractor 不能 approve、reject、close task。

验收：

```text
python -m unittest discover -s apps/contractor/hermes-contractor -p "test_*.py"
powershell -NoProfile -ExecutionPolicy Bypass -File apps/contractor/hermes-contractor/run-smoke.ps1
```

## 工作包 B：真实 Lark 通知与话题组接入

负责方：多多

分支：

```text
feature/duoduo-board-interface
```

目标：

- 使用真实 lark-cli 配置发送任务通知。
- 每个 task_id 只创建一个话题引用。
- 所有消息带 task_id。
- 通知失败返回 `success=False`，并保留 `errors` / `failed_actions`。
- Lark 失败只影响 frontend sync，不改变核心 task state。
- 真实配置只放本地 AgentOps/config，不进入 GitHub。

验收：

```text
python -m unittest adapters/lark/test_lark_notifier.py
powershell -NoProfile -ExecutionPolicy Bypass -File apps/board-interface/lark-topic-board/run-smoke.ps1
```

## 工作包 C：事件驱动自动闭环

负责方：Codex + 多多

目标：

```text
Codex 发布任务
-> Board 录入 task 并创建话题
-> Contractor 秒级接单
-> Contractor 执行并提交
-> Board 通知 review-ready
-> Codex 自动 review
-> approved: Board close_task
-> rejected: Board request_revision 并通知原 contractor
```

设计原则：

- 事件驱动优先。
- 轮询只做兜底。
- watcher 不应调用 LLM，除非其身份是 principal 或 contractor。
- Board watcher 永远 zero-agent。

## 联调门禁

正式接入完成前，必须通过：

```text
scripts/run-tests.ps1
scripts/run-local-e2e.ps1
apps/contractor/hermes-contractor/run-smoke.ps1
apps/board-interface/lark-topic-board/run-smoke.ps1
```

正式环境还需新增：

```text
scripts/run-formal-adapter-smoke.ps1
```

该脚本应验证：

- dry-run Lark 成功。
- invalid Lark 配置失败可观测。
- Hermes provider 失败可观测。
- task 不会因 frontend sync 失败而被关闭。

## 验收结论格式

每次正式接入验收写入 AgentOps：

```text
AgentOps/results/{task_id}-formal-integration.md
AgentOps/latest.md
```

必须包含：

- 使用分支和 commit。
- 协议版本。
- 实现版本。
- 测试命令和结果。
- 真实平台是否启用。
- 是否存在降级 fallback。
- 是否可以进入下一个 release。
