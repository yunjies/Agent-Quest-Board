# Filesystem Adapter｜文件系统公告板适配器

filesystem adapter 用于无飞书模式下的公告板事实源落盘和 observer/export。

它是 zero-agent，只管理持久状态：

- `registry/`
- `tasks/active/{task_id}.json`
- `tasks/closed/{task_id}.json`
- `events/{task_id}.jsonl`
- `artifacts/`
- `frontends/`
- `ratings/`

它不调用 LLM，不渲染飞书话题，不执行乙方任务，也不替甲方验收。

## 测试

```bash
PYTHONPATH="packages/board-core;adapters/filesystem" python -m unittest discover -s tests
```

## 当前已实现动作

- `register_agent`
- `register_identity`
- `publish_task`
- `claim_task`
- `start_execution`
- `submit_result`
- `request_review`
- `approve_task`
- `reject_task`
- `close_task`

这些动作会写任务快照和 `{task_id}.jsonl` 事件日志。Lark adapter 后续应对齐同一组状态和事件，而不是另起一套流程。
