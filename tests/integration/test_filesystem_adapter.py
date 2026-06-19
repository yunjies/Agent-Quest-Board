import json
import tempfile
import unittest
from pathlib import Path

from agent_delegation_filesystem import (
    approve_task,
    claim_task,
    close_task,
    init_board,
    load_task,
    publish_task,
    register_identity,
    request_review,
    start_execution,
    submit_result,
)


class FilesystemAdapterTest(unittest.TestCase):
    def test_publish_submit_review_and_close_without_lark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            task = _task()

            publish_task(root, task, "principal-codex-pc")
            self.assertEqual(load_task(root, "task-no-lark-001")["status"], "published")

            claim_task(root, "task-no-lark-001", "contractor-duoduo")
            start_execution(root, "task-no-lark-001", "contractor-duoduo")
            submit_result(
                root,
                "task-no-lark-001",
                "contractor-duoduo",
                "results/task-no-lark-001.md",
                {"smoke": "passed"},
            )
            request_review(root, "task-no-lark-001", "board-duoduo")
            approve_task(
                root,
                "task-no-lark-001",
                "principal-codex-pc",
                "reviews/task-no-lark-001.md",
            )
            close_task(root, "task-no-lark-001", "board-duoduo")

            closed = load_task(root, "task-no-lark-001")
            self.assertEqual(closed["status"], "closed")
            self.assertFalse((root / "tasks" / "active" / "task-no-lark-001.json").exists())
            self.assertTrue((root / "tasks" / "closed" / "task-no-lark-001.json").exists())

            events = _read_events(root / "events" / "task-no-lark-001.jsonl")
            self.assertEqual(events[0]["type"], "task_published")
            self.assertIn("result_submitted", [event["type"] for event in events])
            self.assertEqual(events[-1]["type"], "task_closed")

    def test_contractor_cannot_submit_unassigned_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
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
            publish_task(root, _task(), "principal-codex-pc")

            with self.assertRaises(Exception):
                submit_result(
                    root,
                    "task-no-lark-001",
                    "contractor-other",
                    "results/wrong.md",
                )

    def test_board_generates_canonical_task_id_for_principal_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            draft = _task_draft()

            published = publish_task(root, draft, "principal-codex-pc")

            self.assertRegex(published["task_id"], r"^aq_\d{8}T\d{9}Z_[A-Z2-9]{4}$")
            self.assertEqual(published["task_id_source"], "board_generated")
            self.assertEqual(load_task(root, published["task_id"])["status"], "published")
            self.assertTrue((root / "events" / f"{published['task_id']}.jsonl").exists())

    def test_publish_is_idempotent_for_same_principal_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)

            first = publish_task(root, _task_draft(), "principal-codex-pc")
            second = publish_task(root, _task_draft(), "principal-codex-pc")

            self.assertEqual(first["task_id"], second["task_id"])


def _register_default_identities(root):
    register_identity(
        root,
        {
            "identity_id": "principal-codex-pc",
                    "agent_id": "agent-codex",
                    "role_type": "principal",
                    "permissions": [
                        "publish_task",
                        "review_task",
                        "approve_task",
                        "reject_task",
                    ],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )
    register_identity(
        root,
        {
            "identity_id": "contractor-duoduo",
                    "agent_id": "agent-duoduo",
                    "role_type": "contractor",
                    "permissions": ["claim_task", "start_execution", "submit_result"],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )
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


def _task():
    return {
        "task_id": "task-no-lark-001",
        "title": "No Lark task",
        "principal_identity_id": "principal-codex-pc",
        "contractor_identity_id": "contractor-duoduo",
        "board_identity_id": "board-duoduo",
        "status": "published",
        "board_protocol_version": "1.0",
    }


def _task_draft():
    return {
        "title": "Board generated task",
        "principal_identity_id": "principal-codex-pc",
        "contractor_identity_id": "contractor-duoduo",
        "board_identity_id": "board-duoduo",
        "status": "draft",
        "board_protocol_version": "1.0",
        "client_request_id": "codex-test-board-generated-task",
        "idempotency_key": "same-key",
    }


def _read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
