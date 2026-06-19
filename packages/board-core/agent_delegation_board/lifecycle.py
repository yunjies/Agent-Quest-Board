from .permissions import (
    PermissionError,
    assert_identity_owns_task,
    check_identity_capability,
)
from .state_machine import StateTransitionError, transition
from .validation import validate_task


class BoardLifecycleError(ValueError):
    pass


def publish_task(store, task, actor_identity_id):
    actor = store.get_identity(actor_identity_id)
    check_identity_capability(actor, "publish_task")
    assert_identity_owns_task(actor_identity_id, task, "principal_identity_id")
    if hasattr(store, "assign_task_identity"):
        task = store.assign_task_identity(dict(task))
        if task.pop("_idempotent_existing", False):
            existing = store.load_task(task["task_id"])
            assert_identity_owns_task(actor_identity_id, existing, "principal_identity_id")
            return existing
    task["status"] = "published"
    validate_task(task)
    _assert_task_identity(store, task["contractor_identity_id"], "contractor")
    if task.get("board_identity_id"):
        _assert_task_identity(store, task["board_identity_id"], "board")
    if task.get("status") != "published":
        raise BoardLifecycleError("published task snapshot must have status=published")

    store.create_active_task(task)
    store.append_event(
        task["task_id"],
        "task_published",
        actor_identity_id,
        {"task_path": store.task_ref(task["task_id"])},
    )
    return task


def claim_task(store, task_id, contractor_identity_id):
    task = store.load_task(task_id)
    actor = store.get_identity(contractor_identity_id)
    check_identity_capability(actor, "claim_task")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    return transition_task(
        store,
        task_id,
        "accepted_by_contractor",
        contractor_identity_id,
        {"event": "task_claimed"},
    )


def start_execution(store, task_id, contractor_identity_id):
    task = store.load_task(task_id)
    actor = store.get_identity(contractor_identity_id)
    check_identity_capability(actor, "start_execution")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    return transition_task(
        store,
        task_id,
        "running",
        contractor_identity_id,
        {"event": "execution_started"},
    )


def submit_result(store, task_id, contractor_identity_id, result_file, artifacts=None):
    task = store.load_task(task_id)
    actor = store.get_identity(contractor_identity_id)
    check_identity_capability(actor, "submit_result")
    assert_identity_owns_task(contractor_identity_id, task, "contractor_identity_id")
    task["result_file"] = result_file
    task["artifacts"] = artifacts or task.get("artifacts", {})
    store.save_active_task(task)
    store.append_event(
        task_id,
        "result_submitted",
        contractor_identity_id,
        {"result_file": result_file, "artifacts": artifacts or {}},
    )
    return transition_task(store, task_id, "submitted", contractor_identity_id)


def request_review(store, task_id, board_identity_id):
    task = store.load_task(task_id)
    actor = store.get_identity(board_identity_id)
    check_identity_capability(actor, "request_review")
    if task.get("board_identity_id") and task["board_identity_id"] != board_identity_id:
        raise PermissionError("board identity does not match task board_identity_id")
    store.append_event(task_id, "review_requested", board_identity_id, {})
    return transition_task(store, task_id, "reviewing", board_identity_id)


def approve_task(store, task_id, principal_identity_id, review_file=None):
    task = store.load_task(task_id)
    actor = store.get_identity(principal_identity_id)
    check_identity_capability(actor, "approve_task")
    assert_identity_owns_task(principal_identity_id, task, "principal_identity_id")
    task["review_verdict"] = "approved"
    if review_file:
        task["review_file"] = review_file
    store.save_active_task(task)
    store.append_event(
        task_id,
        "review_approved",
        principal_identity_id,
        {"review_file": review_file} if review_file else {},
    )
    return transition_task(store, task_id, "approved", principal_identity_id)


def reject_task(store, task_id, principal_identity_id, review_file, revision_request):
    if not revision_request:
        raise BoardLifecycleError("revision_request is required when rejecting")
    task = store.load_task(task_id)
    actor = store.get_identity(principal_identity_id)
    check_identity_capability(actor, "reject_task")
    assert_identity_owns_task(principal_identity_id, task, "principal_identity_id")
    task["review_verdict"] = "rejected"
    task["review_file"] = review_file
    task["revision_request"] = revision_request
    store.save_active_task(task)
    store.append_event(
        task_id,
        "review_rejected",
        principal_identity_id,
        {"review_file": review_file, "revision_request": revision_request},
    )
    transition_task(store, task_id, "rejected", principal_identity_id)
    return transition_task(
        store,
        task_id,
        "revision_requested",
        principal_identity_id,
    )


def transition_task(store, task_id, target_status, actor_identity_id, payload=None):
    task = store.load_active_task(task_id)
    try:
        task["status"] = transition(task["status"], target_status)
    except StateTransitionError as exc:
        store.append_event(
            task_id,
            "incident_created",
            actor_identity_id,
            {"error": str(exc), "target_status": target_status},
        )
        raise

    store.save_active_task(task)
    store.append_event(
        task_id,
        "status_changed",
        actor_identity_id,
        {"status": target_status, **(payload or {})},
    )
    return task


def close_task(store, task_id, actor_identity_id):
    actor = store.get_identity(actor_identity_id)
    check_identity_capability(actor, "close_task")
    task = store.load_active_task(task_id)
    if task.get("board_identity_id") and task["board_identity_id"] != actor_identity_id:
        raise PermissionError("board identity does not match task board_identity_id")
    if task.get("status") != "approved":
        raise BoardLifecycleError("only approved tasks can be closed")

    task["status"] = transition("approved", "closed")
    store.close_active_task(task)
    store.append_event(task_id, "task_closed", actor_identity_id, {})
    return task


def _assert_task_identity(store, identity_id, expected_role):
    identity = store.get_identity(identity_id)
    if identity["role_type"] != expected_role:
        raise PermissionError(
            f"identity {identity_id} must be role {expected_role}, got {identity['role_type']}"
        )
    return identity
