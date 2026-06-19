"""Hermes Contractor — Duoduo-side contractor implementation.

Uses board-generated canonical aq_* task_ids exclusively. All lifecycle
operations (claim, start execution, submit result) go through the filesystem
adapter which delegates to board-core lifecycle.
"""

import json
from pathlib import Path

from agent_delegation_board.task_identity import generate_task_id

try:
    from agent_delegation_filesystem import (
        claim_task as fs_claim_task,
        load_task as fs_load_task,
        register_identity as fs_register_identity,
        start_execution as fs_start_execution,
        submit_result as fs_submit_result,
    )
except ImportError:
    # fallback for direct imports in test context
    from adapters.filesystem.agent_delegation_filesystem.board_store import (
        claim_task as fs_claim_task,
        load_task as fs_load_task,
        register_identity as fs_register_identity,
        start_execution as fs_start_execution,
        submit_result as fs_submit_result,
    )


class HermesContractorError(RuntimeError):
    pass


class HermesContractor:
    """Duoduo-side contractor that operates with canonical aq_* task IDs.

    The contractor:
    - Claims tasks assigned by the board using canonical aq_* IDs.
    - Starts execution and submits results using aq_* IDs exclusively.
    - Processes inbox directories for file-based task delivery.
    - Never generates or assigns its own task IDs — the board owns identity.
    """

    def __init__(self, board_root, identity_id="contractor-duoduo", permissions=None):
        self.board_root = Path(board_root)
        self.identity_id = identity_id
        self.permissions = permissions or [
            "claim_task", "accept_assignment", "start_execution",
            "submit_result", "request_clarification", "mark_blocked",
            "revise_task", "resubmit_result",
        ]

    # ── Identity management ───────────────────────────────────────

    def ensure_registered(self):
        """Register this contractor identity with the board if not already."""
        try:
            fs_load_task(self.board_root, "__check__")
        except Exception:
            pass
        fs_register_identity(self.board_root, {
            "identity_id": self.identity_id,
            "agent_id": "hermes-agent",
            "role_type": "contractor",
            "permissions": self.permissions,
            "board_protocol_version": "1.0",
            "status": "active",
            "display_name": "Duoduo/Hermes Contractor",
        })

    # ── Core operations (canonical aq_* task_id) ──────────────────

    def claim_task(self, task_id):
        """Claim a task by its canonical aq_* task_id.

        Args:
            task_id: Board-generated canonical task_id (format: aq_*).

        Returns:
            Task dict after claim.

        Raises:
            HermesContractorError: If task_id doesn't look canonical or claim fails.
        """
        self._ensure_canonical(task_id)
        try:
            return fs_claim_task(self.board_root, task_id, self.identity_id)
        except Exception as exc:
            raise HermesContractorError(f"claim_task failed for {task_id}: {exc}") from exc

    def start_execution(self, task_id):
        """Start execution of a claimed task by canonical task_id.

        Args:
            task_id: Board-generated canonical task_id.

        Returns:
            Task dict after status transition.

        Raises:
            HermesContractorError: If start_execution fails.
        """
        self._ensure_canonical(task_id)
        try:
            return fs_start_execution(self.board_root, task_id, self.identity_id)
        except Exception as exc:
            raise HermesContractorError(
                f"start_execution failed for {task_id}: {exc}"
            ) from exc

    def submit_result(self, task_id, result_file, artifacts=None):
        """Submit execution result for a task by canonical task_id.

        Args:
            task_id: Board-generated canonical task_id.
            result_file: Path to the result file.
            artifacts: Optional list of artifact paths.

        Returns:
            Task dict after result submission.

        Raises:
            HermesContractorError: If submit_result fails.
        """
        self._ensure_canonical(task_id)
        try:
            return fs_submit_result(
                self.board_root, task_id, self.identity_id,
                str(result_file), artifacts=artifacts,
            )
        except Exception as exc:
            raise HermesContractorError(
                f"submit_result failed for {task_id}: {exc}"
            ) from exc

    # ── Inbox processing ─────────────────────────────────────────

    def fetch_published_tasks(self):
        """List all published tasks from the board store.

        Returns:
            List of task dicts that are in 'published' status.
        """
        active_dir = self.board_root / "tasks" / "active"
        if not active_dir.exists():
            return []
        tasks = []
        for path in sorted(active_dir.glob("*.json")):
            task = json.loads(path.read_text(encoding="utf-8"))
            if task.get("status") == "published":
                tasks.append(task)
        return tasks

    def process_inbox(self, inbox_dir, execute_task_fn):
        """Main loop: read inbox → claim → execute → submit.

        Args:
            inbox_dir: Directory containing task files to process.
            execute_task_fn: Callable(task) that executes the task and
                             returns (result_file_path, artifacts_list).

        Returns:
            List of (task_id, status) tuples for processed tasks.
        """
        inbox_path = Path(inbox_dir)
        if not inbox_path.exists():
            return []

        results = []
        for task_file in sorted(inbox_path.glob("*_task.json")):
            task = json.loads(task_file.read_text(encoding="utf-8"))
            task_id = task.get("task_id")
            if not task_id:
                continue

            try:
                self.claim_task(task_id)
                self.start_execution(task_id)
                result_path, artifacts = execute_task_fn(task)
                self.submit_result(task_id, result_path, artifacts=artifacts)
                results.append((task_id, "submitted"))
            except Exception as exc:
                results.append((task_id, f"failed: {exc}"))

        return results

    # ── Validation helpers ───────────────────────────────────────

    @staticmethod
    def _ensure_canonical(task_id):
        """Assert that task_id follows the aq_* canonical format."""
        if not task_id or not task_id.startswith("aq_"):
            raise HermesContractorError(
                f"canonical aq_* task_id required, got: {task_id!r}"
            )
