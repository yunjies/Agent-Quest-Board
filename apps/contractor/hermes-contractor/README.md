# Hermes Contractor App｜Hermes/多多乙方应用

这是 Hermes/多多作为乙方的应用层入口。

当前由多多侧实现具体运行逻辑。本目录只定义应用边界、配置模板和 smoke 占位。

应用链路：

```text
apps/contractor/hermes-contractor
  -> adapters/hermes 或多多运行时适配
  -> board runtime
```

## 本地 smoke

Windows:

```powershell
apps\contractor\hermes-contractor\run-smoke.ps1
```

POSIX shell:

```bash
sh apps/contractor/hermes-contractor/run-smoke.sh
```

当前 smoke 只验证入口存在。多多接入后应扩展为真实接单、执行、提交。
