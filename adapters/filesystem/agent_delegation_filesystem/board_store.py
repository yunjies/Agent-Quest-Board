from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path

from agent_delegation_board import (
    PermissionError,
    ProtocolValidationError,
    StateTransitionError,
    assert_identity_owns_task,
    check_identity_capability,
    check_role_capability,
    is_known_event_type,
    transition,
    validate_event,
    validate_identity,
    validate_task,
)


class FilesystemBoardError(ValueError):
    pass


RUNTIME_DIRS = [
    "registry",
    "tasks/active",
    "tasks/closed",
    "events",
    "artifacts",
    "frontends",
    "ratings",
]


def init_board(root):
    root_path = Path(root)
    for relative in RUNTIME_DIRS:
        (root_path / relative).mkdir(parents=True, exist_ok=True)
    _ensure_json(root_path / "registry" / "agents.json", {})
    _ensure_json(root_path / "registry" / "identities.json", {})
    return root_path


def register_agent(root, agent):
    root_path = init_board(root)
    agent_id = agent.get("agent_id")
    if not agent_id:
        raise FilesystemBoardError("agent_id is required")
    registry_path = root_path / "registry" / "agents.json"
    registry = _read_json(registry_path)
    registry[agent_id] = agent
    _write_json(registry_path, registry)
    return agent


def register_identity(root, identity):
    validate_identity(identity)
    root_path = init_board(root)
    registry_path = root_path / "registry" / "identities.json"
    registry = _read_json(registry_path)
    registry[identity["identity_id"]] = identity
    _write_json(registry_path, registry)
    return identity


def get_identity(root, identity_id):
    registry = _read_json(init_board(root) / "registry" / "identities.json")
    identity = registry.get(identity_id)
    if not identity:
        raise FilesystemBoardError(f"identity not registered: {identity_id}")
    if identity.get("status") != "active":
        raise PermissionError(f"identity is not active: {identity_id}")
    return identity


def publish_task(root, task, actor_identity_id):
    validate_task(task)
    actor = get_identity(root, actor_identity_id)
    check_identity_capability(actor, "publish_task")
    assert_identity_owns_task(actor_identity_id, task, "principal_identity_id")
    _assert_task_identity(root, task["contractor_identity_id"], "contractor")
    if task.get("board_identity_id"):
        _assert_task_identity(root, task["board_identity_id"], "board")

    root_path = init_board(root)
    task_id = _require_task_id(task)
    active_path = root_path / "tasks" / "active" / f"{task_id}.json"
    closed_path = root_path / "tasks" / "closed" / f"{task_id}.json"

    if active_path.exists() or closed_path.exists():
        raise FilesystemBoardError(f"task already exists: {task_id}")
    if task.get("status") != "published":
        raise FilesystemBoardError("published task snapshot must have status=published")

    _write_json(active_path, task)
    append_event(
        root_path,
        task_id,
        "task_published",
        actor_identity_id,
        {"task_path": str(active_path.as_posix())},
    )
    return active_path


def claim_task(root, task_id, contractor_identity_id):
    task = load_task(root, task_id)
    actor = get_identity(root, contractor_identity_id)
    check_identity_capability(actor, "claim_task")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    return transition_task(
        root,
        task_id,
        "accepted_by_contractor",
        contractor_identity_id,
        {"event": "task_claimed"},
    )


def start_execution(root, task_id, contractor_identity_id):
    task = load_task(root, task_id)
    actor = get_identity(root, contractor_identity_id)
    check_identity_capability(actor, "start_execution")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    return transition_task(
        root,
        task_id,
        "running",
        contractor_identity_id,
        {"event": "execution_started"},
    )


def submit_result(root, task_id, contractor_identity_id, result_file, artifacts=None):
    task = load_task(root, task_id)
    actor = get_identity(root, contractor_identity_id)
    check_identity_capability(actor, "submit_result")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    task["result_file"] = result_file
    task["artifacts"] = artifacts or task.get("artifacts", {})
    _save_active_task(root, task)
    append_event(
        root,
        task_id,
        "result_submitted",
        contractor_identity_id,
        {"result_file": result_file, "artifacts": artifacts or {}},
    )
    return transition_task(root, task_id, "submitted", contractor_identity_id)


def request_review(root, task_id, board_identity_id):
    task = load_task(root, task_id)
    actor = get_identity(root, board_identity_id)
    check_identity_capability(actor, "request_review")
    if task.get("board_identity_id") and task["board_identity_id"] != board_identity_id:
        raise PermissionError("board identity does not match task board_identity_id")
    append_event(root, task_id, "review_requested", board_identity_id, {})
    return transition_task(root, task_id, "reviewing", board_identity_id)


def approve_task(root, task_id, principal_identity_id, review_file=None):
    task = load_task(root, task_id)
    actor = get_identity(root, principal_identity_id)
    check_identity_capability(actor, "approve_task")
    assert_identity_owns_task(principal_identity_id, task, "principal_identity_id")
    task["review_verdict"] = "approved"
    if review_file:
        task["review_file"] = review_file
    _save_active_task(root, task)
    append_event(
        root,
        task_id,
        "review_approved",
        principal_identity_id,
        {"review_file": review_file} if review_file else {},
    )
    return transition_task(root, task_id, "approved", principal_identity_id)


def reject_task(root, task_id, principal_identity_id, review_file, revision_request):
    if not revision_request:
        raise FilesystemBoardError("revision_request is required when rejecting")
    task = load_task(root, task_id)
    actor = get_identity(root, principal_identity_id)
    check_identity_capability(actor, "reject_task")
    assert_identity_owns_task(principal_identity_id, task, "principal_identity_id")
    task["review_verdict"] = "rejected"
    task["review_file"] = review_file
    task["revision_request"] = revision_request
    _save_active_task(root, task)
    append_event(
        root,
        task_id,
        "review_rejected",
        principal_identity_id,
        {"review_file": review_file, "revision_request": revision_request},
    )
    transition_task(root, task_id, "rejected", principal_identity_id)
    return transition_task(root, task_id, "revision_requested", principal_identity_id)


def load_task(root, task_id):
    root_path = Path(root)
    active_path = root_path / "tasks" / "active" / f"{task_id}.json"
    closed_path = root_path / "tasks" / "closed" / f"{task_id}.json"
    if active_path.exists():
        return _read_json(active_path)
    if closed_path.exists():
        return _read_json(closed_path)
    raise FilesystemBoardError(f"task not found: {task_id}")


def transition_task(root, task_id, target_status, actor_identity_id, payload=None):
    root_path = init_board(root)
    active_path = root_path / "tasks" / "active" / f"{task_id}.json"
    if not active_path.exists():
        raise FilesystemBoardError(f"active task not found: {task_id}")

    task = _read_json(active_path)
    try:
        task["status"] = transition(task["status"], target_status)
    except StateTransitionError as exc:
        append_event(
            root_path,
            task_id,
            "incident_created",
            actor_identity_id,
            {"error": str(exc), "target_status": target_status},
        )
        raise

    task["updated_at"] = _now()
    _write_json(active_path, task)
    append_event(
        root_path,
        task_id,
        "status_changed",
        actor_identity_id,
        {"status": target_status, **(payload or {})},
    )
    return task


def close_task(root, task_id, actor_identity_id):
    root_path = init_board(root)
    active_path = root_path / "tasks" / "active" / f"{task_id}.json"
    closed_path = root_path / "tasks" / "closed" / f"{task_id}.json"
    if not active_path.exists():
        raise FilesystemBoardError(f"active task not found: {task_id}")

    actor = get_identity(root_path, actor_identity_id)
    check_identity_capability(actor, "close_task")
    task = _read_json(active_path)
    if task.get("board_identity_id") and task["board_identity_id"] != actor_identity_id:
        raise PermissionError("board identity does not match task board_identity_id")
    if task.get("status") != "approved":
        raise FilesystemBoardError("only approved tasks can be closed")

    task["status"] = transition("approved", "closed")
    task["updated_at"] = _now()
    _write_json(closed_path, task)
    active_path.unlink()
    append_event(root_path, task_id, "task_closed", actor_identity_id, {})
    return closed_path


def append_event(root, task_id, event_type, actor_identity_id, payload=None):
    if not is_known_event_type(event_type):
        raise ProtocolValidationError(f"unknown event type: {event_type}")
    root_path = init_board(root)
    timestamp = _now()
    event = {
        "event_id": _event_id(
            task_id,
            event_type,
            actor_identity_id,
            payload or {},
            timestamp,
        ),
        "task_id": task_id,
        "type": event_type,
        "actor_identity_id": actor_identity_id,
        "timestamp": timestamp,
        "payload": payload or {},
    }
    validate_event(event)
    event_path = root_path / "events" / f"{task_id}.jsonl"
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _assert_task_identity(root, identity_id, expected_role):
    identity = get_identity(root, identity_id)
    if identity["role_type"] != expected_role:
        raise PermissionError(
            f"identity {identity_id} must be role {expected_role}, got {identity['role_type']}"
        )
    return identity


def _save_active_task(root, task):
    validate_task(task)
    task["updated_at"] = _now()
    _write_json(
        init_board(root) / "tasks" / "active" / f"{task['task_id']}.json",
        task,
    )


def _require_task_id(task):
    task_id = task.get("task_id")
    if not task_id:
        raise FilesystemBoardError("task_id is required")
    return task_id


def _ensure_json(path, default):
    if not path.exists():
        _write_json(path, default)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _now():
    return datetime.now(timezone.utc).isoformat()


def _event_id(task_id, event_type, actor_identity_id, payload, timestamp):
    digest = sha1(
        json.dumps(
            {
                "task_id": task_id,
                "type": event_type,
                "actor_identity_id": actor_identity_id,
                "payload": payload,
                "timestamp": timestamp,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"event-{digest}"
