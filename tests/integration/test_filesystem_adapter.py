import tempfile
import unittest
from pathlib import Path

from agent_delegation_filesystem import (
    close_task,
    init_board,
    load_task,
    publish_task,
    transition_task,
)


class FilesystemAdapterTest(unittest.TestCase):
    def test_publish_transition_and_close_without_lark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            task = {
                "task_id": "task-no-lark-001",
                "title": "No Lark task",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }

            publish_task(root, task, "principal-codex-pc")
            self.assertEqual(load_task(root, "task-no-lark-001")["status"], "published")

            transition_task(root, "task-no-lark-001", "accepted_by_contractor", "board-duoduo")
            transition_task(root, "task-no-lark-001", "running", "contractor-duoduo")
            transition_task(root, "task-no-lark-001", "submitted", "contractor-duoduo")
            transition_task(root, "task-no-lark-001", "reviewing", "principal-codex-pc")
            transition_task(root, "task-no-lark-001", "approved", "principal-codex-pc")
            close_task(root, "task-no-lark-001", "board-duoduo")

            self.assertFalse((root / "tasks" / "active" / "task-no-lark-001.json").exists())
            self.assertTrue((root / "tasks" / "closed" / "task-no-lark-001.json").exists())
            self.assertTrue((root / "events" / "task-no-lark-001.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
