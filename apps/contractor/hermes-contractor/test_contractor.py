"""Tests for HermesContractor."""
import json
import sys
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

    def test_execution_log_persisted(self):
        """execution_log 必须写入 task snapshot 和 artifacts/event。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "exec-log-task")
            c = HermesContractor(root, results_dir=str(root / "results"), logs_dir=str(root / "logs"))
            c.ensure_registered()
            c.claim_task("exec-log-task")
            c.start_execution("exec-log-task")

            result = c.execute_task("exec-log-task")
            c.submit_result(
                "exec-log-task",
                result_file=result["result_file"],
                artifacts=result["artifacts"],
                execution_log=result["execution_log"],
            )

            # 1. task snapshot 含 execution_log
            snapshot = c.load_task("exec-log-task")
            self.assertIn("execution_log", snapshot,
                          f"execution_log missing in snapshot keys: {list(snapshot.keys())}")

            # 2. result_submitted event payload artifacts 含 execution_log
            events_dir = root / "events"
            events_path = events_dir / "exec-log-task.jsonl"
            events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
            submitted_events = [e for e in events if e["type"] == "result_submitted"]
            self.assertEqual(len(submitted_events), 1,
                             f"expected 1 result_submitted event, got {len(submitted_events)}")
            payload = submitted_events[0].get("payload", {})
            artifacts = payload.get("artifacts", {})
            self.assertIn("execution_log", artifacts,
                          f"execution_log missing in event payload artifacts: {payload}")

    def test_submit_without_execution_log_still_works(self):
        """不传 execution_log 时应该正常工作，不抛异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _setup_board(root, "no-log-task")
            c = HermesContractor(root, results_dir=str(root / "results"), logs_dir=str(root / "logs"))
            c.ensure_registered()
            c.claim_task("no-log-task")
            c.start_execution("no-log-task")
            result = c.execute_task("no-log-task")

            # 不传 execution_log
            submitted = c.submit_result("no-log-task", result_file=result["result_file"])
            self.assertEqual(submitted["status"], "submitted")

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


class TestExecutionProvider(unittest.TestCase):
    """Tests for ExecutionProvider pluggable interface."""

    def test_default_executor_creates_result_files(self):
        """DefaultExecutionProvider should create result and log files."""
        import tempfile
        from pathlib import Path
        from agent_delegation_hermes_contractor import DefaultExecutionProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results_dir = root / "results"
            logs_dir = root / "logs"
            provider = DefaultExecutionProvider(
                results_dir=results_dir,
                logs_dir=logs_dir,
            )
            task = {"task_id": "test-001", "title": "Test"}
            outcome = provider.execute(task)

            self.assertTrue(Path(outcome["result_file"]).exists())
            self.assertTrue(Path(outcome["execution_log"]).exists())
            self.assertIn("test-001", outcome["result_file"])

    def test_custom_executor_injected_into_contractor(self):
        """HermesContractor should use a custom ExecutionProvider if provided."""
        import tempfile
        from pathlib import Path
        from agent_delegation_hermes_contractor import ExecutionProvider, HermesContractor

        # Define a custom executor
        class MockExecutor(ExecutionProvider):
            def __init__(self):
                self.called_with = None

            def execute(self, task):
                self.called_with = task
                return {
                    "result_file": "/tmp/mock-result.json",
                    "artifacts": {"mock": True},
                    "execution_log": "/tmp/mock-exec.log",
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from agent_delegation_filesystem import init_board, register_identity
            init_board(root)
            register_identity(root, {
                "identity_id": "contractor-duoduo",
                "agent_id": "agent-duoduo",
                "role_type": "contractor",
                "permissions": ["claim_task"],
                "board_protocol_version": "1.0",
                "status": "active",
            })
            register_identity(root, {
                "identity_id": "principal-codex-pc",
                "agent_id": "agent-codex",
                "role_type": "principal",
                "permissions": ["publish_task"],
                "board_protocol_version": "1.0",
                "status": "active",
            })
            register_identity(root, {
                "identity_id": "board-duoduo",
                "agent_id": "agent-duoduo",
                "role_type": "board",
                "permissions": [],
                "board_protocol_version": "1.0",
                "status": "active",
            })

            mock = MockExecutor()
            c = HermesContractor(root, executor=mock)
            c.ensure_registered()

            # Verify execute_task uses the custom executor
            # First we need a task in the board
            from agent_delegation_filesystem import publish_task
            publish_task(root, {
                "task_id": "executor-test",
                "title": "Executor test",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }, "principal-codex-pc")

            outcome = c.execute_task("executor-test")
            self.assertEqual(outcome["result_file"], "/tmp/mock-result.json")
            self.assertTrue(outcome["artifacts"]["mock"])

    def test_default_executor_used_when_none_provided(self):
        """HermesContractor should use DefaultExecutionProvider when no executor given."""
        import tempfile
        from pathlib import Path
        from agent_delegation_hermes_contractor import HermesContractor, DefaultExecutionProvider

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from agent_delegation_filesystem import init_board, register_identity, publish_task
            init_board(root)
            register_identity(root, {
                "identity_id": "contractor-duoduo",
                "agent_id": "agent-duoduo",
                "role_type": "contractor",
                "permissions": ["claim_task"],
                "board_protocol_version": "1.0",
                "status": "active",
            })
            register_identity(root, {
                "identity_id": "principal-codex-pc",
                "agent_id": "agent-codex",
                "role_type": "principal",
                "permissions": ["publish_task"],
                "board_protocol_version": "1.0",
                "status": "active",
            })
            register_identity(root, {
                "identity_id": "board-duoduo",
                "agent_id": "agent-duoduo",
                "role_type": "board",
                "permissions": [],
                "board_protocol_version": "1.0",
                "status": "active",
            })

            publish_task(root, {
                "task_id": "default-exec-test",
                "title": "Default executor test",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }, "principal-codex-pc")

            c = HermesContractor(root)
            c.ensure_registered()
            self.assertIsInstance(c._executor, DefaultExecutionProvider)

            outcome = c.execute_task("default-exec-test")
            self.assertIn("default-exec-test", outcome["result_file"])
            self.assertTrue(Path(outcome["result_file"]).exists())


class TestHermesExecutionProvider(unittest.TestCase):
    """Tests for HermesExecutionProvider — the real task executor."""

    def _make_provider(self, tmp, command=None):
        results_dir = Path(tmp) / "results"
        logs_dir = Path(tmp) / "logs"
        from agent_delegation_hermes_contractor import HermesExecutionProvider
        return HermesExecutionProvider(
            results_dir=results_dir,
            logs_dir=logs_dir,
            command=command,
        ), results_dir, logs_dir

    def test_execute_with_configured_command_receives_task_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, results_dir, logs_dir = self._make_provider(
                tmp,
                command=[
                    sys.executable,
                    "-c",
                    "import json,sys; task=json.load(sys.stdin); print(task['goal'])",
                ],
            )
            task = {
                "task_id": "test-goal-001",
                "title": "Test with goal",
                "goal": "hello from hermes",
            }
            outcome = provider.execute(task)
            self.assertTrue(Path(outcome["result_file"]).exists())

            log = Path(outcome["execution_log"]).read_text(encoding="utf-8")
            self.assertIn("hello from hermes", log)

            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["success"])
            self.assertEqual(result["exit_code"], 0)
            self.assertIn("hello from hermes", result["stdout"])

    def test_natural_language_fields_are_not_shell_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, _, _ = self._make_provider(tmp)
            task = {
                "task_id": "test-desc-001",
                "title": "Test with description",
                "description": "echo should not run",
            }
            outcome = provider.execute(task)
            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "execution_failed")
            self.assertFalse(result["success"])
            self.assertIn("No execution_command", result["error"])

    def test_execute_with_task_execution_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, _, _ = self._make_provider(tmp)
            task = {
                "task_id": "test-cmd-001",
                "title": "Test with command",
                "execution_command": [
                    sys.executable,
                    "-c",
                    "import json,sys; task=json.load(sys.stdin); print(task['task_id'])",
                ],
            }
            outcome = provider.execute(task)
            log = Path(outcome["execution_log"]).read_text(encoding="utf-8")
            self.assertIn("test-cmd-001", log)

    def test_title_is_not_shell_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, _, _ = self._make_provider(tmp)
            task = {
                "task_id": "test-title-001",
                "title": "echo should not run",
            }
            outcome = provider.execute(task)
            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "execution_failed")
            self.assertNotIn("should not run", result.get("stdout", ""))

    def test_execute_failed_command_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, _, _ = self._make_provider(
                tmp,
                command=[sys.executable, "-c", "import sys; sys.exit(42)"],
            )
            task = {
                "task_id": "test-fail-001",
                "title": "Failing",
                "goal": "natural language task",
            }
            outcome = provider.execute(task)
            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "execution_failed")
            self.assertFalse(result["success"])
            self.assertNotEqual(result["exit_code"], 0)

    def test_execute_without_command_fails_observably(self):
        """没有显式 runner command 时，必须写入 execution_failed。"""
        with tempfile.TemporaryDirectory() as tmp:
            provider, _, _ = self._make_provider(tmp)
            task = {
                "task_id": "test-empty-001",
                "title": "",
            }
            outcome = provider.execute(task)
            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "execution_failed")
            self.assertIn("No execution_command", result.get("error", ""))

    def test_injected_into_contractor_works(self):
        """HermesExecutionProvider 通过 executor 注入到 HermesContractor 中正常工作。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from agent_delegation_filesystem import init_board, register_identity, publish_task
            from agent_delegation_hermes_contractor import HermesContractor, HermesExecutionProvider

            init_board(root)
            for ident in [
                {"identity_id": "principal-codex-pc", "agent_id": "agent-codex",
                 "role_type": "principal", "permissions": ["publish_task"],
                 "board_protocol_version": "1.0", "status": "active"},
                {"identity_id": "board-duoduo", "agent_id": "agent-duoduo",
                 "role_type": "board", "permissions": ["append_event", "transition_status"],
                 "board_protocol_version": "1.0", "status": "active"},
            ]:
                register_identity(root, ident)

            provider = HermesExecutionProvider(
                results_dir=root / "results",
                logs_dir=root / "logs",
                command=[
                    sys.executable,
                    "-c",
                    "import json,sys; task=json.load(sys.stdin); print(task['goal'])",
                ],
            )
            c = HermesContractor(root, executor=provider)
            c.ensure_registered()

            publish_task(root, {
                "task_id": "hermes-exec-test",
                "title": "Hermes exec test",
                "goal": "executed by HermesExecutionProvider",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }, "principal-codex-pc")

            c.claim_task("hermes-exec-test")
            c.start_execution("hermes-exec-test")
            outcome = c.execute_task("hermes-exec-test")

            result = json.loads(Path(outcome["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertIn("executed by HermesExecutionProvider", result["stdout"])

    def test_failed_execution_is_not_submitted_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from agent_delegation_filesystem import init_board, register_identity, publish_task, load_task
            from agent_delegation_hermes_contractor import HermesContractor, HermesExecutionProvider

            init_board(root)
            for ident in [
                {"identity_id": "principal-codex-pc", "agent_id": "agent-codex",
                 "role_type": "principal", "permissions": ["publish_task"],
                 "board_protocol_version": "1.0", "status": "active"},
                {"identity_id": "board-duoduo", "agent_id": "agent-duoduo",
                 "role_type": "board", "permissions": ["append_event", "transition_status"],
                 "board_protocol_version": "1.0", "status": "active"},
            ]:
                register_identity(root, ident)

            provider = HermesExecutionProvider(
                results_dir=root / "results",
                logs_dir=root / "logs",
                command=[sys.executable, "-c", "import sys; sys.exit(42)"],
            )
            c = HermesContractor(root, executor=provider)
            c.ensure_registered()

            publish_task(root, {
                "task_id": "hermes-fail-test",
                "title": "Hermes fail test",
                "goal": "natural language task",
                "principal_identity_id": "principal-codex-pc",
                "contractor_identity_id": "contractor-duoduo",
                "board_identity_id": "board-duoduo",
                "status": "published",
                "board_protocol_version": "1.0",
            }, "principal-codex-pc")

            c.claim_task("hermes-fail-test")
            c.start_execution("hermes-fail-test")
            outcome = c.execute_task("hermes-fail-test")

            with self.assertRaises(HermesContractorError):
                c.submit_result(
                    "hermes-fail-test",
                    result_file=outcome["result_file"],
                    artifacts=outcome["artifacts"],
                    execution_log=outcome["execution_log"],
                )

            task = load_task(root, "hermes-fail-test")
            self.assertEqual(task["status"], "needs_user_action")


if __name__ == "__main__":
    unittest.main()
