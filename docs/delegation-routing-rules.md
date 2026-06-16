# 委托路由规则

本文档定义甲方在发布任务前的分流规则，避免把所有需要多多参与的请求都创建为正式委托。

## Lane

### direct_query

不创建正式委托，不创建 task_id。

适用场景：

- 查询 latest 状态
- 读取 result、review、log
- 查看某个文件是否存在
- 简单解释已有输出
- 不产生持久变更的轻量检查

### whitelist_command

创建委托，但由白名单命令执行器处理。

适用场景：

- 任务包含明确的 `Allowed Commands`
- 命令在白名单前缀内
- 不需要 LLM 理解任务内容

### hermes_agent

创建委托，由 Hermes agent 执行。

适用场景：

- 修改 Hermes/AgentOps 脚本
- 写入多多 wiki 或 skill
- 操作飞书/Lark 集成
- 需要环境排查、配置、部署
- 需要 result/review-ready/返工闭环

### delegation_proposal

先创建草案，不直接派单。

适用场景：

- 权限边界不清
- 可能涉及协议版本或安全语义变化
- 不确定甲方/乙方/公告板谁负责

## 示例

| 请求 | lane | 原因 |
|:--|:--|:--|
| 查询 latest 状态 | direct_query | 只读，无持久变更 |
| 读取 review-20260616-03.md | direct_query | 只读 |
| 运行 py_compile smoke | whitelist_command | 命令明确且可白名单化 |
| 修改公告板 Lark 话题状态显示 | hermes_agent | 需要开发、测试、产出验收证据 |
| 沉淀 Hermes 底层机制到多多 wiki | hermes_agent | 需要写入长期知识库 |
| 修改 board_protocol_version 兼容语义 | delegation_proposal | 协议边界变化，需要先确认 |

## 输出要求

路由判断必须保留 `decision_reason`。对于 `direct_query`，甲方应直接响应，不应创建正式公告板任务。
