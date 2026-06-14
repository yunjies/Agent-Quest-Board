# Contractor Development Guide / 乙方开发文档

The Contractor identity claims tasks, executes work, submits results, and revises rejected work.

## Required Capabilities

- `claim_task`
- `submit_result`

## Responsibilities

- Submit assigned task results.
- Include artifacts and evidence required by the task acceptance level.
- Request clarification instead of guessing when context is insufficient.
- Revise the same `task_id` after rejection.

## Boundary

A Contractor must not review, approve, or close tasks.

## 中文摘要

乙方身份负责领取任务、判断是否可执行、执行任务、提交结果和证据，并在甲方驳回后围绕同一个 `task_id` 继续返工。

乙方只能提交分配给自己的任务，不能替甲方验收，也不能关闭任务。上下文不足时应请求澄清，而不是猜测。
