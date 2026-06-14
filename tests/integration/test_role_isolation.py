import unittest

PRINCIPAL_PERMISSIONS = {"publish_task", "review_task", "score_contractor"}
CONTRACTOR_PERMISSIONS = {"claim_task", "submit_result"}
BOARD_PERMISSIONS = {"append_event", "transition_status", "route_notification"}


class RoleIsolationTest(unittest.TestCase):
    def test_principal_cannot_submit_result(self):
        self.assertNotIn("submit_result", PRINCIPAL_PERMISSIONS)

    def test_contractor_cannot_review_task(self):
        self.assertNotIn("review_task", CONTRACTOR_PERMISSIONS)

    def test_board_cannot_execute_task_content(self):
        self.assertNotIn("execute_task", BOARD_PERMISSIONS)


if __name__ == "__main__":
    unittest.main()
