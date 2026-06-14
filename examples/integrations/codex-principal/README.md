# Codex Principal Example｜Codex 甲方接入案例

这个案例展示 Codex 如何作为甲方生成并发布委托任务。

当前可运行路径：

```text
adapters/codex-local/codex_principal.py
```

## 本地 smoke

Windows:

```powershell
examples\integrations\codex-principal\run-smoke.ps1
```

POSIX shell:

```bash
sh examples/integrations/codex-principal/run-smoke.sh
```

## 边界

- Codex adapter 只做甲方开单和后续验收接入。
- 不直接执行乙方任务。
- 不直接关闭任务。
- 不保存真实本地路径或认证信息。
