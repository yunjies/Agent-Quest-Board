# AgentOps Adapter｜AgentOps 本地运行时适配器

AgentOps adapter 用于把公告板协议数据连接到本地 AgentOps 运行目录。

## 边界

- 公开仓库不保存真实运行路径。
- 公开仓库不保存真实 local instance ID。
- 公开仓库不保存密钥、token、chat_id。
- 真实部署配置只应存在本地 AgentOps。

AgentOps 是部署与运行数据目录，不是上游代码仓库。
