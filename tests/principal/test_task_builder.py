import unittest

from agent_delegation_principal import (
    DelegationInput,
    PrincipalTaskError,
    build_task_spec,
    choose_acceptance_level,
    score_delegation,
)


class PrincipalTaskBuilderTest(unittest.TestCase):
    def test_low_score_task_requires_acceptance_tests(self):
        task_input = DelegationInput(
            title="Fix it",
            description="Fix the issue.",
            principal_identity_id="principal-codex-pc",
            contractor_identity_id="contractor-duoduo",
        )

        with self.assertRaises(PrincipalTaskError):
            build_task_spec(task_input)

    def test_build_task_spec_with_score_and_acceptance(self):
        task_input = DelegationInput(
            title="Implement filesystem observer export",
            description=(
                "Create a filesystem observer export for the board runtime. "
                "It should serialize active task snapshots and event summaries "
                "without depending on any Lark adapter."
            ),
            principal_identity_id="principal-codex-pc",
            contractor_identity_id="contractor-duoduo",
            board_identity_id="board-duoduo",
            context=["Board is zero-agent", "Filesystem must work without Lark"],
            acceptance_tests=["Unit tests pass", "No-Lark smoke fixture is generated"],
            constraints=["Do not commit local paths"],
        )

        payload = build_task_spec(task_input)

        self.assertEqual(payload["status"], "draft")
        self.assertNotIn("task_id", payload)
        self.assertEqual(payload["principal_identity_id"], "principal-codex-pc")
        self.assertIn("client_request_id", payload)
        self.assertIn("idempotency_key", payload)
        self.assertGreaterEqual(payload["delegation_score"], 5)
        self.assertIn(payload["acceptance_level"], {"smoke_required", "test_required"})

    def test_acceptance_level_for_low_score(self):
        self.assertEqual(choose_acceptance_level(4), "test_required")
        self.assertEqual(choose_acceptance_level(5), "smoke_required")
        self.assertEqual(choose_acceptance_level(9, "documentation"), "report_only")

    def test_score_breakdown_is_deterministic(self):
        task_input = DelegationInput(
            title="Document protocol",
            description="Write a concise protocol note with examples and limits.",
            principal_identity_id="principal-codex-pc",
            contractor_identity_id="contractor-duoduo",
            context=["Existing protocol version is 1.0"],
            acceptance_tests=["Document has examples"],
        )
        first = score_delegation(task_input)
        second = score_delegation(task_input)
        self.assertEqual(first, second)

    def test_description_bom_is_removed(self):
        task_input = DelegationInput(
            title="Handle Windows text files",
            description="\ufeffImplement a task builder check with explicit evidence.",
            principal_identity_id="principal-codex-pc",
            contractor_identity_id="contractor-duoduo",
            acceptance_tests=["Description has no BOM"],
        )

        payload = build_task_spec(task_input)

        self.assertFalse(payload["description"].startswith("\ufeff"))


if __name__ == "__main__":
    unittest.main()
