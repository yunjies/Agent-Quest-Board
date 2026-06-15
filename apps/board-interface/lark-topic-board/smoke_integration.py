"""Lark full-pipeline integration smoke test.

Tests the real pipeline: LarkTopicBoard (event → notification) → LarkNotifier (notification → lark-cli dispatch).

This runs in dry_run mode — no real API calls. Validates:
1. Event routing produces correct notifications
2. Notifications are dispatchable via LarkNotifier
3. Topic lifecycle (assign → close) works through the pipeline
4. Failure observability: invalid notifier config yields success=False, not crash
"""
import json
import os
import sys
import tempfile
from pathlib import Path


def main():
    exit_code = 0

    with tempfile.TemporaryDirectory() as tmp:
        map_store = Path(tmp) / "topic-map.json"

        # ── Step 1: LarkTopicBoard produces notifications ──────────────
        from agent_delegation_lark_topic_board import LarkTopicBoard
        board = LarkTopicBoard(mapping_store=str(map_store))

        events = [
            {"type": "task_published", "task_id": "integration-001",
             "actor_identity_id": "principal-codex-pc",
             "payload": {"title": "Integration smoke"}},
            {"type": "result_submitted", "task_id": "integration-001",
             "actor_identity_id": "contractor-duoduo",
             "payload": {"title": "Integration smoke"}},
            {"type": "review_rejected", "task_id": "integration-001",
             "actor_identity_id": "principal-codex-pc",
             "payload": {"title": "Integration smoke", "revision_request": "Add more tests"}},
            {"type": "review_approved", "task_id": "integration-001",
             "actor_identity_id": "principal-codex-pc",
             "payload": {"title": "Integration smoke"}},
            {"type": "task_closed", "task_id": "integration-001",
             "actor_identity_id": "board-duoduo", "payload": {}},
            {"type": "incident_created", "task_id": "integration-001",
             "actor_identity_id": "board-duoduo",
             "payload": {"error": "Lark API timeout test"}},
        ]
        tasks = [{"task_id": "integration-001", "title": "Integration smoke"}]

        notifications = board.batch_process_events(events, tasks=tasks)
        assert len(notifications) == 6, f"Expected 6 notifications, got {len(notifications)}"
        print(f"OK Step 1: {len(notifications)} notifications generated from {len(events)} events")

        # ── Step 2: LarkNotifier dispatches notifications (dry_run) ────
        from agent_delegation_lark import LarkNotifier

        notifier = LarkNotifier(
            topic_group_id="test-topic-group",
            dry_run=True,
            lark_cli_bin="echo",
        )

        dispatch_count = 0
        for n in notifications:
            result = notifier.dispatch(n)
            assert result["success"] is True, f"Dispatch failed: {result}"
            dispatch_count += 1
        print(f"OK Step 2: {dispatch_count} notifications dispatched (dry_run=True)")

        # ── Step 3: Topic lifecycle ─────────────────────────────────────
        board.assign_topic("integration-001", "topic-integration-001")
        entry = board.get_topic_for_task("integration-001")
        assert entry["topic_id"] == "topic-integration-001", f"Topic mismatch: {entry}"
        assert board.is_topic_active("integration-001"), "Topic should be active"

        notifier_after_assign = LarkNotifier(dry_run=True, lark_cli_bin="echo")
        closed_notif = board.handle_event(
            {"type": "task_published", "task_id": "integration-001",
             "actor_identity_id": "principal-codex-pc",
             "payload": {"title": "Integration test"}},
            task={"title": "test"}
        )
        # Add topic_id to notification
        closed_notif["topic_id"] = entry

        board.close_topic("integration-001")
        assert not board.is_topic_active("integration-001"), "Topic should be closed"
        print("OK Step 3: topic lifecycle (assign → close) verified")

        # ── Step 4: Failure observability ──────────────────────────────
        notifier_fail = LarkNotifier(
            topic_group_id="test-group",
            incident_chat_id="test-incident-chat",
            dry_run=False,
            lark_cli_bin="/nonexistent/lark-cli-binary",
        )
        # Trigger a topic creation (needs_topic_creation=True, has topic_group_id)
        # The /nonexistent binary will cause FileNotFoundError in _create_topic
        fail_result = notifier_fail.dispatch({
            "task_id": "integration-001",
            "event_type": "incident_created",
            "route": "notify_incident",
            "title": "Test failure",
            "body": "Test failure dispatch",
            "topic_id": None,
            "needs_topic_creation": True,
        })
        # Should not crash — should return success=False with errors
        assert fail_result["success"] is False, f"Should fail: {fail_result}"
        assert len(fail_result.get("errors", [])) > 0 or len(fail_result.get("failed_actions", [])) > 0, \
            f"Should report errors: {fail_result}"
        print(f"OK Step 4: failure observability — success=False, "
              f"errors={fail_result.get('errors', [])}, "
              f"failed_actions={len(fail_result.get('failed_actions', []))}")

    print("ALL OK: Lark full-pipeline integration smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
