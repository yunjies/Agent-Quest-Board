"""Tests for HermesContractor."""
import json
import tempfile
import unittest
from pathlib import Path

from agent_delegation_filesystem import init_board, register_identity, publish_task
from agent_delegation_hermes_contractor import HermesContractor, HermesContractorError


def _setup_board(root, task_id="test-task-001"):
    """Create a minimal board with identities and one published task."""
    init_board(root)
    # Register contractor
    register_identity(
        root,
        {
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
        },
    )
    # Register principal
    register_identity(
        root,
        {
            "identity_id": "principal-codex-pc",
            "agent_id": "agent-codex",
            "role_type": "principal",
            "permissions": ["publish_task", "review_task", "approve_task", "reject_task"],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )
    # Register board
    register_identity(
        root,
        {
            "identity_id": "board-duoduo",
            "agent_id": "agent-duoduo",
            "role_type": "board",
            "permissions": [
                "append_event",
                "transition_status",
                "route_notification",
                "request_review",
                "close_task",
            ],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )
    # Publish task
    task = {
        "task_id": task_id,
        "title": "Test task",
        "principal_identity_id": "principal-codex-pc",
        "contractor_identity_id": "contractor-duoduo",
        "board_identity_id": "board-duoduo",
        "status": "published",
        "board_protocol_version": "1.0",
    }
    publish_task(root, task, "principal-codex-pc")
    return task


class HermesContractorTest(unittest.TestCase):
    def test_ensure_registered_creates_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            c = HermesContractor(root)
            ident = c.ensure_registered()
            self.assertEqual(ident["identity_id"], "contractor-duoduo")
            self.assertEqual(ident["role_type"], "contractor")

    def test_get_assigned_tasks_returns_matching_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "task-1")
            c = HermesContractor(root)
            c.ensure_registered()
            tasks = c.get_assigned_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["task_id"], "task-1")

    def test_get_assigned_tasks_skips_other_contractors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "task-for-me")
            # Manually create a task for another contractor
            register_identity(
                root,
                {
                    "identity_id": "contractor-other",
                    "agent_id": "agent-other",
                    "role_type": "contractor",
                    "permissions": ["claim_task"],
                    "board_protocol_version": "1.0",
                    "status": "active",
                },
            )
            other_task = {
                "task_id": "task-for-other",
                "title": "Not for me",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-other",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }
            publish_task(root, other_task, "principal-codex-pc")

            c = HermesContractor(root)
            c.ensure_registered()
            tasks = c.get_assigned_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["task_id"], "task-for-me")

    def test_full_lifecycle_claim_execute_submit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "lifecycle-task")
            c = HermesContractor(root, results_dir=str(root / "results"), logs_dir=str(root / "logs"))
            c.ensure_registered()

            # Claim
            claimed = c.claim_task("lifecycle-task")
            self.assertEqual(claimed["status"], "accepted_by_contractor")

            # Start execution
            started = c.start_execution("lifecycle-task")
            self.assertEqual(started["status"], "running")

            # Execute
            result = c.execute_task("lifecycle-task")
            self.assertTrue(Path(result["result_file"]).exists())

            # Submit
            submitted = c.submit_result(
                "lifecycle-task",
                result_file=result["result_file"],
                artifacts=result["artifacts"],
            )
            self.assertEqual(submitted["status"], "submitted")
            self.assertEqual(submitted.get("contractor_identity_id"), "contractor-duoduo")

    def test_blocked_on_no_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "block-task")
            c = HermesContractor(root)
            c.ensure_registered()
            c.claim_task("block-task")

            blocked = c.mark_blocked("block-task", "need more context on acceptance criteria")
            self.assertEqual(blocked["status"], "needs_user_action")

    def test_cannot_mark_blocked_after_submitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "block-fail")
            c = HermesContractor(root, results_dir=str(root / "results"), logs_dir=str(root / "logs"))
            c.ensure_registered()
            c.claim_task("block-fail")
            c.start_execution("block-fail")
            result = c.execute_task("block-fail")
            c.submit_result("block-fail", result_file=result["result_file"])

            with self.assertRaises((HermesContractorError, Exception)):
                c.mark_blocked("block-fail", "too late")

    def test_clarification_creates_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "clarify-task")
            c = HermesContractor(root)
            c.ensure_registered()
            event = c.request_clarification("clarify-task", "What is the expected format?")
            self.assertEqual(event["type"], "clarification_requested")
            self.assertEqual(event["payload"]["question"], "What is the expected format?")

    def test_cannot_submit_unassigned_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "my-task")
            # Publish task for another contractor
            register_identity(
                root,
                {
                    "identity_id": "contractor-other",
                    "agent_id": "agent-other",
                    "role_type": "contractor",
                    "permissions": ["claim_task", "submit_result"],
                    "board_protocol_version": "1.0",
                    "status": "active",
                },
            )
            publish_task(
                root,
                {
                    "task_id": "other-task",
                    "title": "Not mine",
                    "principal_identity_id": "principal-codex-pc",
                    "contractor_identity_id": "contractor-other",
                    "board_identity_id": "board-duoduo",
                    "status": "published",
                    "board_protocol_version": "1.0",
                },
                "principal-codex-pc",
            )
            c = HermesContractor(root)
            c.ensure_registered()
            with self.assertRaises(Exception):
                c.claim_task("other-task")


if __name__ == "__main__":
    unittest.main()
