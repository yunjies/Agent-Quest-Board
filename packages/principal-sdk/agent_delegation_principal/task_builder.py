from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256


class PrincipalTaskError(ValueError):
    pass


@dataclass(frozen=True)
class DelegationInput:
    title: str
    description: str
    principal_identity_id: str
    contractor_identity_id: str
    board_identity_id: str = "board-unassigned"
    board_protocol_version: str = "1.0"
    task_kind: str = "coding"
    context: list[str] = field(default_factory=list)
    acceptance_tests: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    client_request_id: str = ""
    idempotency_key: str = ""


def score_delegation(task_input):
    """Return a 0-10 clarity score and a deterministic breakdown."""
    description_words = _word_count(task_input.description)
    breakdown = {
        "description_detail": _score_range(description_words, 30, 180, 0, 3),
        "context": min(len(task_input.context), 2),
        "acceptance_tests": min(len(task_input.acceptance_tests), 3),
        "constraints": min(len(task_input.constraints), 2),
    }
    score = min(10, sum(breakdown.values()))
    return score, breakdown


def choose_acceptance_level(delegation_score, task_kind="coding"):
    if task_kind in {"documentation", "research"} and delegation_score >= 8:
        return "report_only"
    if delegation_score <= 4:
        return "test_required"
    return "smoke_required"


def build_task_spec(task_input):
    description = task_input.description.lstrip("\ufeff").strip()
    if not task_input.title.strip():
        raise PrincipalTaskError("title is required")
    if not description:
        raise PrincipalTaskError("description is required")
    if not task_input.principal_identity_id.strip():
        raise PrincipalTaskError("principal_identity_id is required")
    if not task_input.contractor_identity_id.strip():
        raise PrincipalTaskError("contractor_identity_id is required")

    delegation_score, score_breakdown = score_delegation(task_input)
    acceptance_level = choose_acceptance_level(delegation_score, task_input.task_kind)

    if delegation_score <= 4 and not task_input.acceptance_tests:
        raise PrincipalTaskError(
            "low-score tasks must include acceptance_tests before publishing"
        )

    client_request_id = task_input.client_request_id.strip() or _client_request_id(
        task_input.title,
        task_input.principal_identity_id,
    )
    idempotency_key = task_input.idempotency_key.strip() or _idempotency_key(
        task_input.title,
        task_input.principal_identity_id,
        task_input.contractor_identity_id,
        description,
    )
    now = datetime.now(timezone.utc).isoformat()
    return {
        "title": task_input.title.strip(),
        "description": description,
        "principal_identity_id": task_input.principal_identity_id,
        "contractor_identity_id": task_input.contractor_identity_id,
        "board_identity_id": task_input.board_identity_id,
        "status": "draft",
        "board_protocol_version": task_input.board_protocol_version,
        "client_request_id": client_request_id,
        "idempotency_key": idempotency_key,
        "task_kind": task_input.task_kind,
        "delegation_score": delegation_score,
        "score_breakdown": score_breakdown,
        "acceptance_level": acceptance_level,
        "acceptance_tests": list(task_input.acceptance_tests),
        "context": list(task_input.context),
        "constraints": list(task_input.constraints),
        "artifacts": dict(task_input.artifacts),
        "created_at": now,
        "updated_at": now,
    }


def _word_count(text):
    return len([part for part in text.replace("\n", " ").split(" ") if part.strip()])


def _score_range(value, low, high, low_score, high_score):
    if value < low:
        return low_score
    if value >= high:
        return high_score
    ratio = (value - low) / (high - low)
    return int(round(low_score + ratio * (high_score - low_score)))


def _client_request_id(title, principal_identity_id):
    slug = "".join(
        part.lower() if part.isalnum() else "-"
        for part in title.strip()
    ).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)[:48] or "request"
    return f"{principal_identity_id}:{slug}"


def _idempotency_key(title, principal_identity_id, contractor_identity_id, description):
    return sha256(
        f"{title}|{principal_identity_id}|{contractor_identity_id}|{description}".encode(
            "utf-8"
        )
    ).hexdigest()
