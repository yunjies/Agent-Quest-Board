# Codex Principal App｜Codex 甲方应用

这是 Codex 作为甲方的应用层入口。

当前实现方式：

```text
apps/principal/codex-principal
  -> adapters/codex-local
  -> packages/principal-sdk
  -> adapters/filesystem 或未来 board runtime
```

## 本地 smoke

Windows:

```powershell
apps\principal\codex-principal\run-smoke.ps1
```

POSIX shell:

```bash
sh apps/principal/codex-principal/run-smoke.sh
```

当前 smoke 覆盖：

```text
publish task
simulate contractor submit_result
request_review
Codex principal review approved
board close_task
```

## 后续扩展

- 增加 review-ready 轮询或事件订阅。
- 接入真实 AgentOps board root。
