from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path

from agent_delegation_board import (
    BoardLifecycleError,
    PermissionError,
    ProtocolValidationError,
    is_known_event_type,
    validate_event,
    validate_identity,
    validate_task,
)
from agent_delegation_board.task_identity import generate_task_id
from agent_delegation_board.lifecycle import (
    approve_task as lifecycle_approve_task,
    claim_task as lifecycle_claim_task,
    close_task as lifecycle_close_task,
    publish_task as lifecycle_publish_task,
    reject_task as lifecycle_reject_task,
    request_review as lifecycle_request_review,
    start_execution as lifecycle_start_execution,
    submit_result as lifecycle_submit_result,
    transition_task as lifecycle_transition_task,
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


class FilesystemBoardStore:
    def __init__(self, root):
        self.root = init_board(root)

    def register_agent(self, agent):
        agent_id = agent.get("agent_id")
        if not agent_id:
            raise FilesystemBoardError("agent_id is required")
        registry_path = self.root / "registry" / "agents.json"
        registry = _read_json(registry_path)
        registry[agent_id] = agent
        _write_json(registry_path, registry)
        return agent

    def register_identity(self, identity):
        validate_identity(identity)
        registry_path = self.root / "registry" / "identities.json"
        registry = _read_json(registry_path)
        registry[identity["identity_id"]] = identity
        _write_json(registry_path, registry)
        return identity

    def get_identity(self, identity_id):
        registry = _read_json(self.root / "registry" / "identities.json")
        identity = registry.get(identity_id)
        if not identity:
            raise FilesystemBoardError(f"identity not registered: {identity_id}")
        if identity.get("status") != "active":
            raise PermissionError(f"identity is not active: {identity_id}")
        return identity

    def assign_task_identity(self, task):
        """Assign the canonical board-owned task_id before publication.

        Principals submit drafts with client_request_id/idempotency_key. Existing
        task_id values are kept only for legacy/import compatibility.
        """
        if task.get("task_id"):
            task.setdefault("legacy_task_id", task["task_id"])
            return task

        principal_id = task.get("principal_identity_id", "")
        idempotency_key = task.get("idempotency_key")
        if idempotency_key:
            existing_id = self._lookup_idempotency(principal_id, idempotency_key)
            if existing_id and self.task_exists(existing_id):
                task["task_id"] = existing_id
                task["_idempotent_existing"] = True
                return task

        task["task_id"] = generate_task_id()
        task["task_id_source"] = "board_generated"
        if idempotency_key:
            self._record_idempotency(principal_id, idempotency_key, task["task_id"])
        return task

    def create_active_task(self, task):
        validate_task(task)
        task_id = _require_task_id(task)
        active_path = self._active_task_path(task_id)
        closed_path = self._closed_task_path(task_id)
        if active_path.exists() or closed_path.exists():
            raise FilesystemBoardError(f"task already exists: {task_id}")
        _write_json(active_path, task)
        return active_path

    def task_exists(self, task_id):
        return self._active_task_path(task_id).exists() or self._closed_task_path(task_id).exists()

    def load_task(self, task_id):
        active_path = self._active_task_path(task_id)
        closed_path = self._closed_task_path(task_id)
        if active_path.exists():
            return _read_json(active_path)
        if closed_path.exists():
            return _read_json(closed_path)
        raise FilesystemBoardError(f"task not found: {task_id}")

    def load_active_task(self, task_id):
        active_path = self._active_task_path(task_id)
        if not active_path.exists():
            raise FilesystemBoardError(f"active task not found: {task_id}")
        return _read_json(active_path)

    def save_active_task(self, task):
        validate_task(task)
        task["updated_at"] = _now()
        _write_json(self._active_task_path(task["task_id"]), task)
        return task

    def close_active_task(self, task):
        task["updated_at"] = _now()
        closed_path = self._closed_task_path(task["task_id"])
        _write_json(closed_path, task)
        active_path = self._active_task_path(task["task_id"])
        if active_path.exists():
            active_path.unlink()
        return closed_path

    def append_event(self, task_id, event_type, actor_identity_id, payload=None):
        if not is_known_event_type(event_type):
            raise ProtocolValidationError(f"unknown event type: {event_type}")
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
        with self._event_path(task_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def task_ref(self, task_id):
        return str(self._active_task_path(task_id).as_posix())

    def _active_task_path(self, task_id):
        return self.root / "tasks" / "active" / f"{task_id}.json"

    def _closed_task_path(self, task_id):
        return self.root / "tasks" / "closed" / f"{task_id}.json"

    def _event_path(self, task_id):
        return self.root / "events" / f"{task_id}.jsonl"

    def _idempotency_path(self):
        return self.root / "registry" / "idempotency.json"

    def _lookup_idempotency(self, principal_identity_id, idempotency_key):
        registry = _read_json(self._idempotency_path())
        return registry.get(_idempotency_registry_key(principal_identity_id, idempotency_key))

    def _record_idempotency(self, principal_identity_id, idempotency_key, task_id):
        registry_path = self._idempotency_path()
        registry = _read_json(registry_path)
        registry[_idempotency_registry_key(principal_identity_id, idempotency_key)] = task_id
        _write_json(registry_path, registry)


def init_board(root):
    root_path = Path(root)
    for relative in RUNTIME_DIRS:
        (root_path / relative).mkdir(parents=True, exist_ok=True)
    _ensure_json(root_path / "registry" / "agents.json", {})
    _ensure_json(root_path / "registry" / "identities.json", {})
    _ensure_json(root_path / "registry" / "idempotency.json", {})
    return root_path


def register_agent(root, agent):
    return FilesystemBoardStore(root).register_agent(agent)


def register_identity(root, identity):
    return FilesystemBoardStore(root).register_identity(identity)


def get_identity(root, identity_id):
    return FilesystemBoardStore(root).get_identity(identity_id)


def publish_task(root, task, actor_identity_id):
    return lifecycle_publish_task(
        FilesystemBoardStore(root),
        task,
        actor_identity_id,
    )


def claim_task(root, task_id, contractor_identity_id):
    return lifecycle_claim_task(
        FilesystemBoardStore(root),
        task_id,
        contractor_identity_id,
    )


def start_execution(root, task_id, contractor_identity_id):
    return lifecycle_start_execution(
        FilesystemBoardStore(root),
        task_id,
        contractor_identity_id,
    )


def submit_result(root, task_id, contractor_identity_id, result_file, artifacts=None):
    return lifecycle_submit_result(
        FilesystemBoardStore(root),
        task_id,
        contractor_identity_id,
        result_file,
        artifacts,
    )


def request_review(root, task_id, board_identity_id):
    return lifecycle_request_review(
        FilesystemBoardStore(root),
        task_id,
        board_identity_id,
    )


def approve_task(root, task_id, principal_identity_id, review_file=None):
    return lifecycle_approve_task(
        FilesystemBoardStore(root),
        task_id,
        principal_identity_id,
        review_file,
    )


def reject_task(root, task_id, principal_identity_id, review_file, revision_request):
    try:
        return lifecycle_reject_task(
            FilesystemBoardStore(root),
            task_id,
            principal_identity_id,
            review_file,
            revision_request,
        )
    except BoardLifecycleError as exc:
        raise FilesystemBoardError(str(exc)) from exc


def load_task(root, task_id):
    return FilesystemBoardStore(root).load_task(task_id)


def transition_task(root, task_id, target_status, actor_identity_id, payload=None):
    return lifecycle_transition_task(
        FilesystemBoardStore(root),
        task_id,
        target_status,
        actor_identity_id,
        payload,
    )


def close_task(root, task_id, actor_identity_id):
    try:
        lifecycle_close_task(FilesystemBoardStore(root), task_id, actor_identity_id)
    except BoardLifecycleError as exc:
        raise FilesystemBoardError(str(exc)) from exc
    return FilesystemBoardStore(root)._closed_task_path(task_id)


def append_event(root, task_id, event_type, actor_identity_id, payload=None):
    return FilesystemBoardStore(root).append_event(
        task_id,
        event_type,
        actor_identity_id,
        payload,
    )


def _require_task_id(task):
    task_id = task.get("task_id")
    if not task_id:
        raise FilesystemBoardError("task_id is required")
    return task_id


def _idempotency_registry_key(principal_identity_id, idempotency_key):
    return f"{principal_identity_id}:{idempotency_key}"


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
