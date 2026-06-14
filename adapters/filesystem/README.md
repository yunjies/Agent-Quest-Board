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
