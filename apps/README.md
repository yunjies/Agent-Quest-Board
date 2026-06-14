# Apps｜应用层

`apps/` 只放可运行应用和接入编排，不放协议规则和引擎逻辑。

应用层可以引用：

```text
packages/*
adapters/*
examples/*
```

应用层不应该反向污染：

```text
protocol/
packages/board-core/
```

## 三类应用

```text
principal/        甲方实现
contractor/       乙方实现
board-interface/  公告板前端 interface 接入
```

## 边界

- 甲方应用负责开单、验收、评分。
- 乙方应用负责接单、执行、提交、返工。
- 公告板前端 interface 负责展示、通知、话题/面板同步。
- 公告板核心状态、权限、事件和关闭规则仍由引擎层提供。

真实配置不得提交到仓库。使用 `config.example.yaml` 作为模板，真实配置放到本地部署目录或环境变量。

## 什么时候只改 apps

以下情况只应修改 `apps/`，必要时配合 `adapters/`：

- 新增一个甲方 Agent。
- 新增一个乙方 Agent。
- 新增一个公告板前端。
- 改某个具体 Agent 的运行方式。
- 改某个平台的认证、路径、轮询、通知方式。

## 什么时候不能只改 apps

以下情况需要修改 `protocol/` 或 `packages/board-core/`：

- 新增协议字段。
- 新增状态。
- 新增事件类型。
- 修改权限语义。
- 修改任务生命周期规则。

当前任务生命周期规则位于：

```text
packages/board-core/agent_delegation_board/lifecycle.py
```
