"""Tests for HermesContractor — canonical aq_* task_id integration."""

import json
import tempfile
import unittest
from pathlib import Path

from agent_delegation_filesystem import (
    approve_task,
    init_board,
    load_task,
    publish_task,
    register_identity,
    request_review,
)
from agent_delegation_hermes_contractor import HermesContractor, HermesContractorError


def _register_default_identities(root):
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
                "append_event", "transition_status", "route_notification",
                "request_review", "close_task",
            ],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )


def _publish_canonical_task(root, task_id=None):
    """Create and publish a task with canonical aq_* or custom task_id."""
    task = {
        "task_id": task_id,
        "title": "Canonical task_id test",
        "principal_identity_id": "principal-codex-pc",
        "contractor_identity_id": "contractor-duoduo",
        "board_identity_id": "board-duoduo",
        "status": "published" if task_id else "draft",
        "board_protocol_version": "1.0",
    }
    return publish_task(root, task, "principal-codex-pc")


class HermesContractorCanonicalIdTest(unittest.TestCase):
    """Tests that HermesContractor uses canonical aq_* task IDs exclusively."""

    def test_claim_with_canonical_id_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            # Publish with an explicit aq_* canonical ID
            published = _publish_canonical_task(root, "aq_20260619T112015432Z_K7P3")

            contractor = HermesContractor(root, "contractor-duoduo")
            result = contractor.claim_task("aq_20260619T112015432Z_K7P3")

            self.assertEqual(result["status"], "accepted_by_contractor")
            self.assertEqual(result["task_id"], "aq_20260619T112015432Z_K7P3")

    def test_claim_with_canonical_board_generated_id_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            # Publish without task_id — board generates aq_*
            published = _publish_canonical_task(root, None)
            canon_id = published["task_id"]
            self.assertRegex(canon_id, r"^aq_\d{8}T\d{9}Z_[A-Z2-9]{4}$")

            contractor = HermesContractor(root, "contractor-duoduo")
            result = contractor.claim_task(canon_id)

            self.assertEqual(result["status"], "accepted_by_contractor")
            self.assertEqual(result["task_id"], canon_id)

    def test_claim_with_non_canonical_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            _publish_canonical_task(root, "task-legacy-001")

            contractor = HermesContractor(root, "contractor-duoduo")
            with self.assertRaises(HermesContractorError) as ctx:
                contractor.claim_task("task-legacy-001")
            self.assertIn("canonical aq_* task_id required", str(ctx.exception))

    def test_start_execution_with_canonical_id_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            _publish_canonical_task(root, "aq_20260619T112015432Z_K7P3")

            contractor = HermesContractor(root, "contractor-duoduo")
            contractor.claim_task("aq_20260619T112015432Z_K7P3")
            result = contractor.start_execution("aq_20260619T112015432Z_K7P3")

            self.assertEqual(result["status"], "running")

    def test_start_execution_with_non_canonical_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)

            contractor = HermesContractor(root, "contractor-duoduo")
            with self.assertRaises(HermesContractorError) as ctx:
                contractor.start_execution("task-legacy-001")
            self.assertIn("canonical aq_* task_id required", str(ctx.exception))

    def test_submit_result_with_canonical_id_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            _publish_canonical_task(root, "aq_20260619T112015432Z_K7P3")

            contractor = HermesContractor(root, "contractor-duoduo")
            contractor.claim_task("aq_20260619T112015432Z_K7P3")
            contractor.start_execution("aq_20260619T112015432Z_K7P3")

            result_file = root / "results" / "aq_20260619T112015432Z_K7P3.md"
            result_file.parent.mkdir(parents=True, exist_ok=True)
            result_file.write_text("# Result: OK\n", encoding="utf-8")

            result = contractor.submit_result(
                "aq_20260619T112015432Z_K7P3",
                str(result_file),
                artifacts=[],
            )
            self.assertEqual(result["status"], "submitted")

    def test_submit_result_with_non_canonical_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)

            contractor = HermesContractor(root, "contractor-duoduo")
            with self.assertRaises(HermesContractorError) as ctx:
                contractor.submit_result("task-legacy-001", "results/legacy.md")
            self.assertIn("canonical aq_* task_id required", str(ctx.exception))

    def test_full_lifecycle_with_canonical_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            published = _publish_canonical_task(root, None)
            canon_id = published["task_id"]
            self.assertRegex(canon_id, r"^aq_")

            contractor = HermesContractor(root, "contractor-duoduo")

            # Claim
            claimed = contractor.claim_task(canon_id)
            self.assertEqual(claimed["status"], "accepted_by_contractor")

            # Start execution
            started = contractor.start_execution(canon_id)
            self.assertEqual(started["status"], "running")

            # Submit result
            result_file = root / "results" / f"{canon_id}.md"
            result_file.parent.mkdir(parents=True, exist_ok=True)
            result_file.write_text("# Full lifecycle result\n", encoding="utf-8")
            submitted = contractor.submit_result(canon_id, str(result_file), artifacts=[])
            self.assertEqual(submitted["status"], "submitted")

            # Verify events created with canonical ID
            events_path = root / "events" / f"{canon_id}.jsonl"
            self.assertTrue(events_path.exists())
            events = [json.loads(l) for l in events_path.read_text("utf-8").splitlines()]
            event_types = [e["type"] for e in events]
            self.assertIn("task_published", event_types)
            self.assertIn("result_submitted", event_types)
            # status_changed written for claim, start_execution, and submit_result transitions
            status_changed_count = sum(1 for t in event_types if t == "status_changed")
            self.assertEqual(status_changed_count, 3,
                             f"expected 3 status_changed events, got {status_changed_count}: {event_types}")

    def test_legacy_task_preserved_with_legacy_id_field(self):
        """Publishing a task with an explicit task_id preserves it as legacy_task_id."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            task = {
                "task_id": "task-legacy-001",
                "title": "Legacy task",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }
            published = publish_task(root, task, "principal-codex-pc")
            self.assertEqual(published["task_id"], "task-legacy-001")
            self.assertEqual(published.get("legacy_task_id"), "task-legacy-001")
            # Contractor cannot claim legacy IDs — that's correct
            contractor = HermesContractor(root, "contractor-duoduo")
            with self.assertRaises(HermesContractorError):
                contractor.claim_task("task-legacy-001")

    def test_ensure_registered_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            contractor = HermesContractor(root, "contractor-duoduo")
            # Should not raise
            contractor.ensure_registered()

    def test_contractor_cannot_approve(self):
        """Contractor identity isolation — cannot approve/review tasks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            contractor = HermesContractor(root, "contractor-duoduo")

            with self.assertRaises(AttributeError):
                contractor.approve_task  # type: ignore

    def test_smoke_basic_ops_dont_crash(self):
        """Smoke test — constructing and checking identity doesn't crash."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            contractor = HermesContractor(root, "contractor-duoduo")
            self.assertEqual(contractor.identity_id, "contractor-duoduo")
            self.assertIsNotNone(contractor.board_root)

    def test_fetch_published_tasks_with_canonical_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_board(root)
            _register_default_identities(root)
            _publish_canonical_task(root, "aq_20260619T112015432Z_K7P3")
            _publish_canonical_task(root, "aq_20260619T112015432Z_X9B2")

            contractor = HermesContractor(root, "contractor-duoduo")
            tasks = contractor.fetch_published_tasks()

            self.assertEqual(len(tasks), 2)
            for t in tasks:
                self.assertRegex(t["task_id"], r"^aq_")


if __name__ == "__main__":
    unittest.main()
