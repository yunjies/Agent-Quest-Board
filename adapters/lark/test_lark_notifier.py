"""Tests for LarkNotifier — 飞书通知发送器。"""
import tempfile
import unittest

from agent_delegation_lark import LarkNotifier, LarkNotifierError
# We use the board-interface's LarkTopicBoard to generate notifications
from agent_delegation_lark_topic_board import LarkTopicBoard


def _notification(event_type, task_id="task-001", extra=None):
    """Build a notification dict as produced by LarkTopicBoard.handle_event()."""
    event = {
        "type": event_type,
        "task_id": task_id,
        "actor_identity_id": "test-actor",
        "payload": extra or {},
    }
    task = {"task_id": task_id, "title": "Test task"}
    board = LarkTopicBoard(mapping_store=tempfile.mktemp(suffix=".json"))
    return board.handle_event(event, task=task)


class LarkNotifierDryRunTest(unittest.TestCase):
    """Tests that verify LarkNotifier in dry-run mode (no actual API calls)."""

    def setUp(self):
        self.notifier = LarkNotifier(
            topic_group_id="example-topic-group",
            incident_chat_id="example-incident-chat",
            dry_run=True,
        )

    def test_dispatch_task_published(self):
        notif = _notification("task_published")
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("topic_created"))
        self.assertEqual(result.get("topic_id"), "example-dry-run-topic")

    def test_dispatch_result_submitted(self):
        # First assign a topic so the notification carries topic_id
        notif = _notification("result_submitted")
        notif["topic_id"] = "existing-topic"
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("message_sent"))
        self.assertTrue(result.get("topic_status_updated"))
        self.assertEqual(result.get("topic_status_update_mode"), "dry_run_status_update")

    def test_dispatch_review_rejected(self):
        notif = _notification("review_rejected", extra={"revision_request": "Add tests"})
        notif["topic_id"] = "existing-topic"
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("message_sent"))

    def test_dispatch_review_approved(self):
        notif = _notification("review_approved")
        notif["topic_id"] = "existing-topic"
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("close_initiated"))
        self.assertTrue(result.get("topic_status_updated"))

    def test_dispatch_incident(self):
        notif = _notification("incident_created", extra={"error": "API timeout"})
        notif["topic_id"] = "existing-topic"
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        self.assertTrue(result.get("incident_notified"))

    def test_dispatch_unknown_event(self):
        # Unknown events return None from LarkTopicBoard — dispatch should handle None gracefully
        result = self.notifier.dispatch(None)
        self.assertTrue(result["success"])
        self.assertEqual(result.get("notification_type"), None)

    def test_dispatch_no_topic_id(self):
        notif = _notification("result_submitted")
        # No topic_id set — should still be handled gracefully
        result = self.notifier.dispatch(notif)
        self.assertTrue(result["success"])
        # message not sent because no chat_id
        self.assertIsNone(result.get("message_sent"))

    def test_dispatch_batch(self):
        # Batch dispatch multiple notifications
        notifs = [
            _notification("task_published"),
            _notification("result_submitted"),
            _notification("task_closed"),
        ]
        results = self.notifier.dispatch_batch(notifs)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r["success"])

    def test_task_closed_is_logical_close(self):
        notif = _notification("task_closed")
        notif["topic_id"] = "existing-topic"
        result = self.notifier.dispatch(notif)

        self.assertTrue(result["success"])
        self.assertTrue(result["close_initiated"])
        self.assertTrue(result["topic_status_updated"])

    def test_no_topic_group_no_creation(self):
        """When topic_group_id is None, needs_topic_creation should not create a topic."""
        notifier = LarkNotifier(dry_run=True)
        notif = _notification("task_published")
        result = notifier.dispatch(notif)
        self.assertTrue(result["success"])
        # topic_created should not be set because no topic_group_id
        self.assertNotIn("topic_created", result)


class LarkNotifierEdgeCaseTest(unittest.TestCase):
    """Edge cases and error handling tests."""

    def test_invalid_lark_cli_bin(self):
        """If lark-cli doesn't exist, should not crash in dry_run=False."""
        # When in production mode with invalid CLI, should catch FileNotFoundError
        notifier = LarkNotifier(
            topic_group_id="example-topic-group",
            dry_run=False,
            lark_cli_bin="/nonexistent/binary",
        )
        notif = _notification("task_published")
        # Should not crash
        result = notifier.dispatch(notif)
        self.assertFalse(result["success"])
        self.assertFalse(result.get("topic_created", False))
        self.assertIn("failed_actions", result)
        self.assertEqual(result["failed_actions"][0]["action"], "create_topic")

    def test_send_message_failure_marks_dispatch_failed(self):
        notifier = LarkNotifier(dry_run=True)
        notifier._send_message = lambda chat_id, body: {
            "success": False,
            "error": "send failed",
        }
        notif = _notification("result_submitted")
        notif["topic_id"] = "existing-topic"

        result = notifier.dispatch(notif)

        self.assertFalse(result["success"])
        self.assertFalse(result["message_sent"])
        self.assertEqual(result["failed_actions"][0]["action"], "send_message")
        self.assertIn("send failed", result["errors"])

    def test_close_topic_failure_marks_dispatch_failed(self):
        notifier = LarkNotifier(dry_run=True)
        notifier._close_topic = lambda notification: {
            "success": False,
            "error": "close failed",
        }
        notif = _notification("review_approved")
        notif["topic_id"] = "existing-topic"

        result = notifier.dispatch(notif)

        self.assertFalse(result["success"])
        self.assertFalse(result["close_initiated"])
        self.assertEqual(result["failed_actions"][0]["action"], "close_topic")
        self.assertIn("close failed", result["errors"])

    def test_incident_notify_failure_marks_dispatch_failed(self):
        notifier = LarkNotifier(
            incident_chat_id="example-incident-chat",
            dry_run=True,
        )
        notifier._send_message = lambda chat_id, body: {
            "success": False,
            "error": "incident failed",
        }
        notif = _notification("incident_created", extra={"error": "API timeout"})

        result = notifier.dispatch(notif)

        self.assertFalse(result["success"])
        self.assertFalse(result["incident_notified"])
        self.assertEqual(result["failed_actions"][0]["action"], "notify_incident")
        self.assertIn("incident failed", result["errors"])

    def test_dispatch_batch_preserves_individual_failures(self):
        notifier = LarkNotifier(dry_run=True)
        notif_ok = _notification("task_published")
        notif_fail = _notification("result_submitted")
        notif_fail["topic_id"] = "existing-topic"

        original_send = notifier._send_message

        def send_message(chat_id, body):
            if chat_id == "existing-topic":
                return {"success": False, "error": "send failed"}
            return original_send(chat_id, body)

        notifier._send_message = send_message

        results = notifier.dispatch_batch([notif_ok, notif_fail])

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertFalse(results[1]["success"])

    def test_empty_notification_dict(self):
        """Edge case: empty notification dict."""
        notifier = LarkNotifier(dry_run=True)
        result = notifier.dispatch({})
        self.assertTrue(result["success"])  # Graceful handling
        self.assertEqual(result.get("notification_type"), None)
