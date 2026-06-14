from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path

from agent_delegation_board import StateTransitionError, transition


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
    return root_path


def publish_task(root, task, actor_identity_id):
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
    root_path = Path(root)
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
    root_path = Path(root)
    active_path = root_path / "tasks" / "active" / f"{task_id}.json"
    closed_path = root_path / "tasks" / "closed" / f"{task_id}.json"
    if not active_path.exists():
        raise FilesystemBoardError(f"active task not found: {task_id}")

    task = _read_json(active_path)
    if task.get("status") != "approved":
        raise FilesystemBoardError("only approved tasks can be closed")

    task["status"] = transition("approved", "closed")
    task["updated_at"] = _now()
    _write_json(closed_path, task)
    active_path.unlink()
    append_event(root_path, task_id, "task_closed", actor_identity_id, {})
    return closed_path


def append_event(root, task_id, event_type, actor_identity_id, payload=None):
    root_path = init_board(root)
    event = {
        "event_id": _event_id(task_id, event_type, actor_identity_id, payload or {}),
        "task_id": task_id,
        "type": event_type,
        "actor_identity_id": actor_identity_id,
        "timestamp": _now(),
        "payload": payload or {},
    }
    event_path = root_path / "events" / f"{task_id}.jsonl"
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _require_task_id(task):
    task_id = task.get("task_id")
    if not task_id:
        raise FilesystemBoardError("task_id is required")
    return task_id


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _now():
    return datetime.now(timezone.utc).isoformat()


def _event_id(task_id, event_type, actor_identity_id, payload):
    digest = sha1(
        json.dumps(
            {
                "task_id": task_id,
                "type": event_type,
                "actor_identity_id": actor_identity_id,
                "payload": payload,
                "timestamp": _now(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"event-{digest}"
