import unittest

from agent_delegation_board import (
    ProtocolValidationError,
    validate_event,
    validate_identity,
    validate_task,
)


class ValidationTest(unittest.TestCase):
    def test_identity_required_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_identity({"identity_id": "principal-codex-pc"})

    def test_task_score_bounds(self):
        with self.assertRaises(ProtocolValidationError):
            validate_task(
                {
                    "task_id": "task-1",
                    "title": "Task",
                    "principal_identity_id": "principal-codex-pc",
                    "contractor_identity_id": "contractor-duoduo",
                    "status": "published",
                    "board_protocol_version": "1.0",
                    "delegation_score": 11,
                }
            )

    def test_event_payload_must_be_object(self):
        with self.assertRaises(ProtocolValidationError):
            validate_event(
                {
                    "event_id": "event-1",
                    "task_id": "task-1",
                    "type": "task_published",
                    "actor_identity_id": "principal-codex-pc",
                    "timestamp": "2026-06-15T00:00:00+00:00",
                    "payload": "bad",
                }
            )


if __name__ == "__main__":
    unittest.main()
