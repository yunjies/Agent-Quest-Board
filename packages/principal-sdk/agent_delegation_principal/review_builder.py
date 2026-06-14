from dataclasses import dataclass, field
from datetime import datetime, timezone


class PrincipalReviewError(ValueError):
    pass


@dataclass(frozen=True)
class ReviewInput:
    task_id: str
    principal_identity_id: str
    verdict: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    revision_request: str | None = None
    contractor_rating: int | None = None
    rating_breakdown: dict = field(default_factory=dict)


def build_review_payload(review_input):
    if not review_input.task_id.strip():
        raise PrincipalReviewError("task_id is required")
    if not review_input.principal_identity_id.strip():
        raise PrincipalReviewError("principal_identity_id is required")
    if review_input.verdict not in {"approved", "rejected"}:
        raise PrincipalReviewError("verdict must be approved or rejected")
    if not review_input.summary.strip():
        raise PrincipalReviewError("summary is required")
    if review_input.verdict == "rejected" and not (
        review_input.revision_request and review_input.revision_request.strip()
    ):
        raise PrincipalReviewError("rejected reviews require revision_request")
    if review_input.contractor_rating is not None:
        _validate_rating(review_input.contractor_rating)

    payload = {
        "task_id": review_input.task_id,
        "principal_identity_id": review_input.principal_identity_id,
        "review_verdict": review_input.verdict,
        "summary": review_input.summary.strip(),
        "evidence": list(review_input.evidence),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if review_input.revision_request:
        payload["revision_request"] = review_input.revision_request.strip()
    if review_input.contractor_rating is not None:
        payload["contractor_rating"] = review_input.contractor_rating
        payload["rating_breakdown"] = dict(review_input.rating_breakdown)
    return payload


def build_contractor_rating(score, breakdown=None):
    _validate_rating(score)
    return {
        "contractor_rating": score,
        "rating_breakdown": dict(breakdown or {}),
    }


def _validate_rating(score):
    if not isinstance(score, int) or score < 0 or score > 10:
        raise PrincipalReviewError("contractor_rating must be an integer 0-10")
