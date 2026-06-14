# Filesystem Adapter

The filesystem adapter renders board state to markdown or JSON views for environments without Lark.

It is intentionally zero-agent. It only manages durable state:

- `registry/`
- `tasks/active/{task_id}.json`
- `tasks/closed/{task_id}.json`
- `events/{task_id}.jsonl`
- `artifacts/`
- `frontends/`
- `ratings/`

It does not call an LLM, render Lark topics, execute contractor work, or review
principal acceptance.

Tests import it with:

```bash
PYTHONPATH="packages/board-core;adapters/filesystem" python -m unittest discover -s tests
```
