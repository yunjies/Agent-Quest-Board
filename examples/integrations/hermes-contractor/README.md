# Hermes Contractor Example｜Hermes/多多乙方接入案例

这个案例展示 Hermes/多多如何作为乙方接入公告板。

当前由多多侧实现具体适配。仓库只提供协议骨架和脱敏配置样例。

## 乙方职责

- 注册 `contractor` identity。
- 领取或接收分配给自己的任务。
- 执行任务。
- 写入 result_file、artifacts、execution_log。
- 对甲方驳回意见围绕同一个 `task_id` 返工。

## 边界

- 不替甲方验收。
- 不关闭任务。
- 不修改非自己分配的任务。
- 上下文不足时请求澄清。
