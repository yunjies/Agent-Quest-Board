# Principal Development Guide / 甲方开发文档

The Principal identity publishes tasks, defines acceptance, reviews results, and scores contractors.

## Required Capabilities

- `publish_task`
- `review_task`
- `score_contractor`

## Responsibilities

- Compute `delegation_score`.
- Set `acceptance_level`.
- Provide actionable rejection feedback.
- Review only tasks published by the same principal identity.

## Boundary

A Principal must not submit contractor results or close tasks directly. Closing is performed by the board after an approved review.

## 中文摘要

甲方身份负责发布委托、给任务评分、定义验收等级、接收 review-ready 信号、验收乙方结果并给乙方评分。

甲方只能验收自己 `principal_identity_id` 发布的任务，不能提交乙方结果。低分任务不能裸发，必须补足上下文、约束和验收测试。
