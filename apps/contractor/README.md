# Contractor Apps｜乙方实现

乙方应用负责把某个 Agent 接成 contractor identity。

职责：

- 注册或声明 contractor identity。
- 领取或接收分配给自己的任务。
- 判断任务是否可执行。
- 执行任务。
- 提交 result、artifact、execution log。
- 响应甲方驳回并返工。

当前 v1 默认实现：

```text
hermes-contractor/
```

乙方应用不能替甲方验收，不能关闭任务，不能提交非自己分配的任务。
