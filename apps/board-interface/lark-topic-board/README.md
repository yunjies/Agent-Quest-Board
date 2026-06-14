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

Windows：

```powershell
apps\board-interface\lark-topic-board\run-smoke.ps1
```

POSIX shell：

```bash
sh apps/board-interface/lark-topic-board/run-smoke.sh
```

当前 smoke 验证事件路由正确性、话题生命周期（assign/close/persist），以及全局 exit code。

## 本地单元测试

Windows：

```powershell
$env:PYTHONPATH='apps/board-interface/lark-topic-board'
python -m unittest discover -s apps\board-interface\lark-topic-board -p "test_*.py"
```

或直接（从项目根目录）：

```powershell
$env:PYTHONPATH='apps/board-interface/lark-topic-board'
python -m unittest apps\board-interface\lark-topic-board\test_board_interface.py
```

POSIX shell：

```bash
PYTHONPATH=apps/board-interface/lark-topic-board \
  python -m unittest discover -s apps/board-interface/lark-topic-board -p "test_*.py"
```

## 测试入口说明

本 app 的测试**不纳入**主入口 `scripts/run-tests.ps1`（该入口覆盖 packages/ 的核心 board lifecycle 测试）。

app 分支的完整验证流程：

1. `scripts\run-tests.ps1` — 核心包测试通过
2. `apps\board-interface\lark-topic-board\run-smoke.ps1` — app smoke 通过  
3. `python -m unittest apps\board-interface\lark-topic-board\test_board_interface.py` — app 单元测试通过

三条都绿才可合并。

## 设计约束

- 当前是 interface skeleton，不接真实 Lark API。
- 所有示例 ID（task-001、example-topic-id 等）均为脱敏值。
- 通知使用固定模板，不从任务内容生成新信息（zero-agent 合规）。
- 不提供 approve_task 或 execute_task 方法（interface 层不做决策）。
