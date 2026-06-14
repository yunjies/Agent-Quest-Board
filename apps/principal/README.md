# Principal Apps｜甲方实现

甲方应用负责把某个 Agent 接成 principal identity。

职责：

- 注册或声明 principal identity。
- 构造委托任务。
- 根据 `delegation_score` 调整开单详细度。
- 发布任务。
- 接收 review-ready 信号。
- 验收、驳回、评分。

当前 v1 默认实现：

```text
codex-principal/
```

甲方应用可以使用：

```text
packages/principal-sdk
adapters/codex-local
adapters/filesystem
```

但甲方应用不能直接关闭任务，也不能提交乙方结果。
