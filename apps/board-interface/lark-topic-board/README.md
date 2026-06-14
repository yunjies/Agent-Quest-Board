# Lark Topic Board Interface｜飞书话题公告板前端

这是飞书话题作为公告板前端 interface 的应用层入口。

应用链路：

```text
apps/board-interface/lark-topic-board
  -> adapters/lark
  -> board runtime
```

飞书只做展示、通知和人工交互入口，不是事实源。

## 本地 smoke

Windows:

```powershell
apps\board-interface\lark-topic-board\run-smoke.ps1
```

POSIX shell:

```bash
sh apps/board-interface/lark-topic-board/run-smoke.sh
```

当前 smoke 只验证入口存在。多多接入 Lark adapter 后，应扩展为创建 topic、路由 task event、写 frontend ref。
