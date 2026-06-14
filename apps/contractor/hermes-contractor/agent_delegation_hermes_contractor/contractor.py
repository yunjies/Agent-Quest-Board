"""Hermes Contractor — 多多乙方身份的实现。

职责：
- 注册 contractor-duoduo 身份。
- 从公告板扫描分配给自己的任务。
- Claim, execute, submit, handle revision。
- 使用 lifecycle.py 的确定性子例程，不走自定义状态机。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from agent_delegation_board.lifecycle import (
    claim_task as lifecycle_claim_task,
    start_execution as lifecycle_start_execution,
    submit_result as lifecycle_submit_result,
    BoardLifecycleError,
)
from agent_delegation_filesystem.board_store import (
    FilesystemBoardStore,
    append_event,
    get_identity,
    load_task,
    register_identity,
)


CONTRACTOR_IDENTITY = {
    "identity_id": "contractor-duoduo",
    "agent_id": "agent-duoduo",
    "role_type": "contractor",
    "permissions": [
        "claim_task",
        "accept_assignment",
        "start_execution",
        "submit_result",
        "request_clarification",
        "mark_blocked",
        "revise_task",
        "resubmit_result",
    ],
    "board_protocol_version": "1.0",
    "status": "active",
}


class HermesContractorError(ValueError):
    pass


class HermesContractor:
    """Contractor 业务逻辑封装。

    所有 board 操作通过 lifecycle.py 的确定性子例程执行。
    """

    def __init__(self, board_root, identity_id=None, results_dir=None, logs_dir=None):
        self.board_root = Path(board_root)
        self.identity_id = identity_id or "contractor-duoduo"
        self.results_dir = Path(results_dir) if results_dir else self.board_root / "results"
        self.logs_dir = Path(logs_dir) if logs_dir else self.board_root / "logs"
        self.store = FilesystemBoardStore(self.board_root)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── 身份注册 ──────────────────────────────────────────────

    def ensure_registered(self):
        """确保 contractor-duoduo 已在 board 注册。"""
        try:
            return get_identity(self.board_root, self.identity_id)
        except Exception:
            return register_identity(self.board_root, dict(CONTRACTOR_IDENTITY))

    # ── 任务扫描 ──────────────────────────────────────────────

    def get_assigned_tasks(self):
        """扫描 board/tasks/active/，返回 contractor_identity_id 匹配的任务列表。"""
        active_dir = self.board_root / "tasks" / "active"
        if not active_dir.is_dir():
            return []
        tasks = []
        for path in sorted(active_dir.glob("*.json")):
            task = json.loads(path.read_text(encoding="utf-8"))
            if task.get("contractor_identity_id") == self.identity_id:
                tasks.append(task)
        return tasks

    def load_task(self, task_id):
        """加载单个任务。"""
        return load_task(self.board_root, task_id)

    # ── 生命周期操作（委托给 lifecycle.py） ─────────────────

    def claim_task(self, task_id):
        """调用 lifecycle.claim_task。"""
        return lifecycle_claim_task(self.store, task_id, self.identity_id)

    def start_execution(self, task_id):
        """调用 lifecycle.start_execution。"""
        return lifecycle_start_execution(self.store, task_id, self.identity_id)

    def submit_result(self, task_id, result_file=None, artifacts=None, execution_log=None):
        """调用 lifecycle.submit_result。

        如果 task 正在 revision_requested 状态，先 transition 到 running。
        """
        task = self.store.load_active_task(task_id)
        if task.get("status") == "revision_requested":
            from agent_delegation_board.lifecycle import transition_task
            transition_task(self.store, task_id, "running", self.identity_id)

        if not result_file:
            result_file = str(self.results_dir / f"{task_id}-result.json")
        return lifecycle_submit_result(
            self.store,
            task_id,
            self.identity_id,
            result_file,
            artifacts or {},
        )

    # ── 异常处理 ──────────────────────────────────────────────

    def mark_blocked(self, task_id, reason):
        """通过 lifecycle 的 transition 将任务标记为 blocked。"""
        from agent_delegation_board.lifecycle import transition_task

        task = self.store.load_active_task(task_id)
        if task.get("status") not in ("published", "accepted_by_contractor", "running", "revision_requested"):
            raise HermesContractorError(
                f"cannot mark blocked from status {task.get('status')}"
            )
        return transition_task(
            self.store,
            task_id,
            "needs_user_action",
            self.identity_id,
            {"reason": reason, "event": "blocked"},
        )

    def request_clarification(self, task_id, question):
        """写入澄清请求事件。"""
        event = append_event(
            self.board_root,
            task_id,
            "clarification_requested",
            self.identity_id,
            {"question": question},
        )
        return event

    # ── 执行抽象 ──────────────────────────────────────────────

    def execute_task(self, task_id):
        """抽象的执行入口。smoke 测试中用 mock 覆盖；生产环境调用 Hermes 执行器。

        返回 dict::
            {"result_file": str, "artifacts": dict, "execution_log": str}
        """
        task = self.store.load_active_task(task_id)
        # 默认实现：写一个 result 占位文件
        result = self._build_default_result(task)
        result_path = self.results_dir / f"{task_id}-result.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        execution_log_path = self.logs_dir / f"{task_id}-execution.log"
        execution_log_path.write_text(
            f"executed_at: {_now()}\ntask_id: {task_id}\nstatus: done\n",
            encoding="utf-8",
        )
        return {
            "result_file": str(result_path),
            "artifacts": result.get("artifacts", {}),
            "execution_log": str(execution_log_path),
        }

    def _build_default_result(self, task):
        return {
            "task_id": task["task_id"],
            "title": task.get("title", ""),
            "contractor_identity_id": self.identity_id,
            "executed_at": _now(),
            "status": "completed",
            "artifacts": {},
        }


def _now():
    return datetime.now(timezone.utc).isoformat()
