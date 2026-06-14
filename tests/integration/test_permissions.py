import unittest

from agent_delegation_board import (
    PermissionError,
    assert_identity_owns_task,
    check_role_capability,
)


class PermissionTest(unittest.TestCase):
    def test_principal_can_review_but_not_submit_result(self):
        self.assertTrue(check_role_capability("principal", "review_task"))
        with self.assertRaises(PermissionError):
            check_role_capability("principal", "submit_result")

    def test_contractor_can_submit_but_not_approve(self):
        self.assertTrue(check_role_capability("contractor", "submit_result"))
        with self.assertRaises(PermissionError):
            check_role_capability("contractor", "approve_task")

    def test_identity_must_match_task_owner_field(self):
        task = {"principal_identity_id": "principal-codex-pc"}
        self.assertTrue(
            assert_identity_owns_task(
                "principal-codex-pc",
                task,
                "principal_identity_id",
            )
        )
        with self.assertRaises(PermissionError):
            assert_identity_owns_task(
                "principal-other",
                task,
                "principal_identity_id",
            )


if __name__ == "__main__":
    unittest.main()
