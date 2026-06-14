# Agent委托公告板

Agent委托公告板是一个协议优先的 Agent 委托协作框架。它把“谁发任务、谁执行任务、谁验收任务、任务在哪里展示、状态如何流转”从具体 Agent 和具体平台中解耦出来。

English README: [README.en.md](README.en.md)

## 三方角色

- **甲方 Principal**：发布委托任务、定义验收标准、验收结果、给乙方评分。
- **乙方 Contractor**：接收或领取任务、执行任务、提交结果、根据驳回意见返工。
- **公告板 Board**：注册身份、校验权限、维护状态机、落盘事件、路由通知、在通过后关闭任务。

甲方和乙方不是固定产品名，而是底层 Agent 注册出的身份。同一个 Agent 可以在不同任务中扮演不同身份。

## 核心原则

- 公告板是 zero-agent：不调用 LLM，不理解任务，不执行任务，不替甲方验收。
- AgentOps/board 是事实源；飞书、Web、Markdown 都只是前端适配器。
- 每个委托任务必须落盘，即使没有飞书也能通过 observer 或 filesystem 前端查看。
- 只有 `approved` 后任务才可以 `closed`；失败、驳回、返工、等待人工都不关闭。
- 甲方/乙方/公告板共享 `board_protocol_version`，只有协议兼容才能对接。

## 当前 v1 分工

- **Codex**：负责框架、协议、基建、测试、甲方 Principal 接入。
- **多多**：负责飞书公告板适配、乙方 Contractor 注册与 Hermes 接入、公告板在多多侧的运行承载。

详细分工见：[docs/development-ownership.md](docs/development-ownership.md)

## 开发与测试

Windows:

```powershell
scripts\run-tests.ps1
```

POSIX shell:

```bash
sh scripts/run-tests.sh
```

当前已实现模块：

- `packages/board-core`：状态机、兼容性、事件类型、角色权限。
- `packages/principal-sdk`：甲方任务评分与任务 payload 构建。
- `adapters/codex-local`：Codex 本地甲方开单 JSON 生成器。
- `adapters/filesystem`：无飞书模式下的公告板落盘适配器。

## 仓库结构

```text
docs/                 产品与集成文档
protocol/             协议版本、兼容矩阵、JSON Schema、fixtures
packages/             共享核心库和 SDK
adapters/             平台/运行时适配器
examples/             示例组件声明
tests/                协议、兼容性、集成测试
```

## Public 仓库安全规则

不要提交真实 chat_id、API key、token、NAS 路径或用户本地配置。所有示例都使用 `.example.json` 或 `.example.yaml`。
