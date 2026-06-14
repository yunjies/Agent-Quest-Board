# Board Interface Apps｜公告板前端 Interface 接入

公告板前端 interface 负责把公告板事实源展示到具体平台或 UI。

职责：

- 创建或绑定任务前端引用。
- 路由任务事件通知。
- 展示状态、结果、验收、incident。
- 在任务 approved 后展示 closed。
- 处理 frontend sync failed，并写入 incident。

它不负责：

- 判断任务质量。
- 执行任务。
- 直接修改协议状态机。
- 替代公告板事实源。

当前 v1 默认 interface：

```text
lark-topic-board/
```
