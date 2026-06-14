import unittest

from agent_delegation_principal import (
    PrincipalReviewError,
    ReviewInput,
    build_contractor_rating,
    build_review_payload,
)


class ReviewBuilderTest(unittest.TestCase):
    def test_approved_review_payload(self):
        payload = build_review_payload(
            ReviewInput(
                task_id="task-001",
                principal_identity_id="principal-codex-pc",
                verdict="approved",
                summary="Result includes required smoke evidence.",
                evidence=["result_file exists", "events contain result_submitted"],
                contractor_rating=8,
                rating_breakdown={"evidence": 4, "quality": 4},
            )
        )

        self.assertEqual(payload["review_verdict"], "approved")
        self.assertEqual(payload["contractor_rating"], 8)
        self.assertIn("reviewed_at", payload)

    def test_rejected_review_requires_revision_request(self):
        with self.assertRaises(PrincipalReviewError):
            build_review_payload(
                ReviewInput(
                    task_id="task-001",
                    principal_identity_id="principal-codex-pc",
                    verdict="rejected",
                    summary="Missing smoke evidence.",
                )
            )

    def test_rejected_review_payload(self):
        payload = build_review_payload(
            ReviewInput(
                task_id="task-001",
                principal_identity_id="principal-codex-pc",
                verdict="rejected",
                summary="Missing smoke evidence.",
                revision_request="Add command output and rerun the smoke check.",
            )
        )

        self.assertEqual(payload["review_verdict"], "rejected")
        self.assertIn("revision_request", payload)

    def test_rating_bounds(self):
        self.assertEqual(build_contractor_rating(10)["contractor_rating"], 10)
        with self.assertRaises(PrincipalReviewError):
            build_contractor_rating(11)


if __name__ == "__main__":
    unittest.main()
