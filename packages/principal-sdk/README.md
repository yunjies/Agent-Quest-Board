# Principal SDK｜甲方 SDK

甲方 SDK 提供甲方身份的确定性辅助能力：

- 构建任务规格。
- 计算任务委托质量分 `delegation_score`。
- 选择验收等级 `acceptance_level`。
- 后续扩展发布任务、提交 review、给乙方评分。

核心协议逻辑仍放在 `packages/board-core`。

## 当前已实现

- `score_delegation`
- `choose_acceptance_level`
- `build_task_spec`
- `build_review_payload`
- `build_contractor_rating`

低分任务不能在没有 `acceptance_tests` 的情况下发布。这样可以避免模糊委托直接变成乙方猜测。

`build_review_payload` 用于生成甲方验收结果。`rejected` 必须提供可执行 `revision_request`。
