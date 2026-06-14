# Examples｜接入样例

本目录分为两类：

```text
minimal/        平台无关的最小协议样例
integrations/   Codex、Hermes、多多、Lark 等真实接入案例
```

## 如何选择

- 只想理解协议：看 `examples/minimal`。
- 要接 Codex 甲方：看 `examples/integrations/codex-principal`。
- 要接 Hermes/多多乙方：看 `examples/integrations/hermes-contractor`。
- 要接多多公告板承载：看 `examples/integrations/duoduo-board`。
- 要接飞书话题前端：看 `examples/integrations/lark-topic-board`。

## 安全规则

example 可以复制和改造，但不能提交真实配置：

- 不提交真实 token / API key / app secret。
- 不提交真实 chat_id / topic_id / open_id。
- 不提交 NAS 路径、本机绝对路径、个人目录。
- 所有真实部署配置放在本地 `.local`、AgentOps 或部署环境变量中。
