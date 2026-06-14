class ProtocolValidationError(ValueError):
    pass


REQUIRED_FIELDS = {
    "identity": {
        "identity_id",
        "agent_id",
        "role_type",
        "permissions",
        "board_protocol_version",
        "status",
    },
    "task": {
        "task_id",
        "title",
        "principal_identity_id",
        "contractor_identity_id",
        "status",
        "board_protocol_version",
    },
    "event": {"event_id", "task_id", "type", "actor_identity_id", "timestamp"},
}


def validate_identity(identity):
    _require_fields("identity", identity)
    if identity["role_type"] not in {"principal", "contractor", "board"}:
        raise ProtocolValidationError(f"invalid role_type: {identity['role_type']}")
    if identity["status"] not in {"active", "disabled"}:
        raise ProtocolValidationError(f"invalid identity status: {identity['status']}")
    if not isinstance(identity["permissions"], list):
        raise ProtocolValidationError("identity permissions must be a list")
    return True


def validate_task(task):
    _require_fields("task", task)
    if task.get("delegation_score") is not None:
        score = task["delegation_score"]
        if not isinstance(score, int) or score < 0 or score > 10:
            raise ProtocolValidationError("delegation_score must be an integer 0-10")
    if task.get("acceptance_level") is not None and task["acceptance_level"] not in {
        "report_only",
        "smoke_required",
        "test_required",
    }:
        raise ProtocolValidationError(
            f"invalid acceptance_level: {task['acceptance_level']}"
        )
    return True


def validate_event(event):
    _require_fields("event", event)
    if not isinstance(event.get("payload", {}), dict):
        raise ProtocolValidationError("event payload must be an object")
    return True


def _require_fields(kind, payload):
    missing = sorted(REQUIRED_FIELDS[kind] - set(payload.keys()))
    if missing:
        raise ProtocolValidationError(
            f"{kind} is missing required fields: {', '.join(missing)}"
        )
