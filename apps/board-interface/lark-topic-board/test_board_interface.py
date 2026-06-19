"""Tests for LarkTopicBoard — 飞书话题公告板前端 Interface。"""
import json
import tempfile
import unittest
from pathlib import Path

from agent_delegation_lark_topic_board import LarkTopicBoard, LarkTopicBoardError


def _event(event_type, task_id="task-001", extra_payload=None):
    """Helper to build a test event."""
    payload = extra_payload or {}
    return {
        "type": event_type,
        "task_id": task_id,
        "actor_identity_id": "test-actor",
        "payload": payload,
    }


class LarkTopicBoardTest(unittest.TestCase):
    # ── 话题映射 ──────────────────────────────────────────

    def test_assign_and_get_topic(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic("task-001", "example-topic-123")
        entry = board.get_topic_for_task("task-001")
        self.assertEqual(entry["topic_id"], "example-topic-123")
        self.assertEqual(entry["status"], "active")

    def test_topic_active_check(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        self.assertIsNone(board.get_topic_for_task("unknown"))
        self.assertFalse(board.is_topic_active("unknown"))

    def test_close_topic_marks_closed(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic("task-001", "example-topic-123")
        self.assertTrue(board.is_topic_active("task-001"))
        board.close_topic("task-001")
        self.assertFalse(board.is_topic_active("task-001"))
        self.assertEqual(board.get_topic_for_task("task-001")["status"], "closed")

    def test_topic_mapping_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "topic-map.json"
            # Write
            board = LarkTopicBoard(mapping_store=str(store))
            board.assign_topic("task-001", "example-topic-123")
            board.assign_topic("task-002", "example-topic-456")
            board.close_topic("task-002")
            # Read back in new instance
            board2 = LarkTopicBoard(mapping_store=str(store))
            self.assertEqual(board2.get_topic_for_task("task-001")["topic_id"], "example-topic-123")
            self.assertEqual(board2.get_topic_for_task("task-002")["status"], "closed")

    # ── 事件路由 ──────────────────────────────────────────

    def test_task_published_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("task_published", extra_payload={"title": "My task"})
        task = {"task_id": "task-001", "title": "My task"}
        notif = board.handle_event(event, task=task)

        self.assertIsNotNone(notif)
        self.assertEqual(notif["route"], "notify_contractor")
        self.assertEqual(notif["to"], "contractor")
        self.assertTrue(notif["needs_topic_creation"])
        self.assertEqual(notif["status_label"], "进行中")
        self.assertIn("[进行中]", notif["display_message"])
        self.assertEqual(notif["topic_update"]["status_label"], "进行中")

    def test_result_submitted_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("result_submitted")
        task = {"task_id": "task-001", "title": "My task"}
        notif = board.handle_event(event, task=task)

        self.assertIsNotNone(notif)
        self.assertEqual(notif["route"], "notify_principal")
        self.assertEqual(notif["to"], "principal")
        self.assertEqual(notif["status_label"], "待验收")
        self.assertTrue(notif["display_title"].startswith("[待验收]"))

    def test_review_rejected_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("review_rejected", extra_payload={"revision_request": "Add test"})
        task = {"task_id": "task-001", "title": "My task"}
        notif = board.handle_event(event, task=task)

        self.assertIsNotNone(notif)
        self.assertEqual(notif["route"], "notify_contractor_revision")
        self.assertEqual(notif["to"], "contractor")
        self.assertIn("Add test", notif["body"])
        self.assertEqual(notif["status_label"], "返工中")

    def test_review_approved_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic("task-001", "example-topic-123")
        event = _event("review_approved")
        task = {"task_id": "task-001", "title": "My task"}
        notif = board.handle_event(event, task=task)

        self.assertIsNotNone(notif)
        self.assertTrue(notif["pending_close"])
        self.assertEqual(notif["topic_id"]["topic_id"], "example-topic-123")
        self.assertEqual(notif["status_label"], "待关闭")
        self.assertTrue(board.is_topic_active("task-001"))

    def test_task_closed_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic("task-001", "example-topic-123")
        event = _event("task_closed")
        notif = board.handle_event(event)

        self.assertIsNotNone(notif)
        self.assertEqual(notif["route"], "close_topic")
        self.assertTrue(notif["pending_close"])
        self.assertTrue(notif["logical_close"])
        self.assertEqual(notif["status_label"], "已关闭")
        self.assertFalse(board.is_topic_active("task-001"))
        self.assertEqual(board.get_topic_for_task("task-001")["status"], "closed")

    def test_incident_notification(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("incident_created", extra_payload={"error": "Lark API timeout"})
        notif = board.handle_event(event)

        self.assertIsNotNone(notif)
        self.assertEqual(notif["route"], "notify_incident")
        self.assertEqual(notif["to"], "operator")

    def test_unknown_event_is_skipped(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("unknown_event_type")
        notif = board.handle_event(event)
        self.assertIsNone(notif)

    # ── 批量处理 ──────────────────────────────────────────

    def test_batch_process_events(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        events = [
            _event("task_published", task_id="task-001", extra_payload={"title": "Task 1"}),
            _event("result_submitted", task_id="task-001"),
            _event("review_rejected", task_id="task-001", extra_payload={"revision_request": "Fix it"}),
        ]
        tasks = [{"task_id": "task-001", "title": "Task 1"}]
        notifications = board.batch_process_events(events, tasks=tasks)
        self.assertEqual(len(notifications), 3)

    # ── Zero-agent 合规 ──────────────────────────────────

    def test_no_llm_calls(self):
        """LarkTopicBoard 不应 import 或引用任何 LLM 相关模块。"""
        import sys
        llm_modules = [m for m in ("transformers", "anthropic", "openai", "deepseek", "langchain") if m in sys.modules]
        self.assertEqual([], llm_modules, f"found LLM modules loaded: {llm_modules}")

    def test_does_not_understand_task_content(self):
        """通知消息使用固定模板，不从任务内容生成新信息。"""
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        event = _event("result_submitted", extra_payload={"some_data": "secret_content"})
        notif = board.handle_event(event)
        # 通知消息不应包含未在模板中定义的 payload 字段
        self.assertNotIn("secret_content", notif["body"])
        self.assertNotIn("some_data", notif["body"])

    def test_cannot_approve_or_execute(self):
        """LarkTopicBoard 不提供 approve_task 或 execute_task 方法。"""
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        with self.assertRaises(AttributeError):
            board.approve_task  # type: ignore
        with self.assertRaises(AttributeError):
            board.execute_task  # type: ignore


class CanonicalTaskIdLarkBoardTest(unittest.TestCase):
    """LarkTopicBoard works with board-generated canonical aq_* task IDs."""

    CANONICAL_ID = "aq_20260619T112015432Z_K7P3"
    CANONICAL_ID_2 = "aq_20260619T112015432Z_X9B2"

    def test_canonical_task_id_topic_mapping(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic(self.CANONICAL_ID, "topic-aq-001")
        entry = board.get_topic_for_task(self.CANONICAL_ID)
        self.assertEqual(entry["topic_id"], "topic-aq-001")
        self.assertEqual(entry["status"], "active")

    def test_canonical_task_id_display_title(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic(self.CANONICAL_ID, "topic-aq-001")

        event = _event("task_published", task_id=self.CANONICAL_ID, extra_payload={"title": "My task"})
        task = {"task_id": self.CANONICAL_ID, "title": "My task"}
        notif = board.handle_event(event, task=task)

        self.assertIsNotNone(notif)
        self.assertIn(self.CANONICAL_ID, notif["display_title"])
        self.assertIn("My task", notif["display_title"])

    def test_canonical_task_id_full_lifecycle(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))

        # Publish
        notif = board.handle_event(
            _event("task_published", task_id=self.CANONICAL_ID, extra_payload={"title": "Canonical test"}),
            task={"task_id": self.CANONICAL_ID, "title": "Canonical test"},
        )
        self.assertIsNotNone(notif)
        self.assertTrue(notif["needs_topic_creation"])

        # Assign topic
        board.assign_topic(self.CANONICAL_ID, "topic-aq-lifecycle")
        self.assertTrue(board.is_topic_active(self.CANONICAL_ID))

        # Result submitted
        notif = board.handle_event(
            _event("result_submitted", task_id=self.CANONICAL_ID),
            task={"task_id": self.CANONICAL_ID, "title": "Canonical test"},
        )
        self.assertEqual(notif["route"], "notify_principal")
        self.assertEqual(notif["status_label"], "待验收")

        # Review approved
        notif = board.handle_event(
            _event("review_approved", task_id=self.CANONICAL_ID),
            task={"task_id": self.CANONICAL_ID, "title": "Canonical test"},
        )
        self.assertTrue(notif["pending_close"])

        # Close
        notif = board.handle_event(
            _event("task_closed", task_id=self.CANONICAL_ID),
        )
        self.assertTrue(notif["logical_close"])
        self.assertFalse(board.is_topic_active(self.CANONICAL_ID))

    def test_canonical_task_id_with_idempotent_topic(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic(self.CANONICAL_ID, "topic-aq-001")

        # Second assignment to same task_id should succeed
        board.assign_topic(self.CANONICAL_ID, "topic-aq-002")
        entry = board.get_topic_for_task(self.CANONICAL_ID)
        self.assertEqual(entry["topic_id"], "topic-aq-002")

    def test_legacy_task_id_format_still_works(self):
        """aq_* format is a new feature; legacy task-xxx format must still work."""
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic("task-legacy-001", "topic-legacy")
        self.assertTrue(board.is_topic_active("task-legacy-001"))
        entry = board.get_topic_for_task("task-legacy-001")
        self.assertEqual(entry["topic_id"], "topic-legacy")

    def test_multiple_canonical_ids_can_coexist(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic(self.CANONICAL_ID, "topic-aq-001")
        board.assign_topic(self.CANONICAL_ID_2, "topic-aq-002")
        self.assertEqual(
            board.get_topic_for_task(self.CANONICAL_ID)["topic_id"], "topic-aq-001"
        )
        self.assertEqual(
            board.get_topic_for_task(self.CANONICAL_ID_2)["topic_id"], "topic-aq-002"
        )

    def test_canonical_task_id_closes_properly(self):
        board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
        board.assign_topic(self.CANONICAL_ID, "topic-aq-close")
        board.close_topic(self.CANONICAL_ID)
        self.assertFalse(board.is_topic_active(self.CANONICAL_ID))
        entry = board.get_topic_for_task(self.CANONICAL_ID)
        self.assertEqual(entry["status"], "closed")


if __name__ == "__main__":
    unittest.main()
