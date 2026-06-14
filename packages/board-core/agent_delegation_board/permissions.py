ROLE_CAPABILITIES = {
    "principal": {
        "publish_task",
        "amend_task",
        "cancel_own_task",
        "review_task",
        "approve_task",
        "reject_task",
        "score_contractor",
    },
    "contractor": {
        "claim_task",
        "accept_assignment",
        "start_execution",
        "submit_result",
        "request_clarification",
        "mark_blocked",
        "revise_task",
        "resubmit_result",
    },
    "board": {
        "register_agent",
        "register_identity",
        "publish_task",
        "append_event",
        "transition_status",
        "assign_contractor",
        "create_topic",
        "route_notification",
        "request_review",
        "request_revision",
        "close_task",
        "create_incident",
        "export_observer_data",
    },
}


class PermissionError(ValueError):
    pass


def check_role_capability(role, capability):
    allowed = ROLE_CAPABILITIES.get(role)
    if allowed is None:
        raise PermissionError(f"Unknown role: {role}")
    if capability not in allowed:
        raise PermissionError(f"{role} cannot perform capability: {capability}")
    return True


def check_identity_capability(identity, capability):
    check_role_capability(identity["role_type"], capability)
    if capability not in identity.get("permissions", []):
        raise PermissionError(
            f"identity {identity['identity_id']} lacks permission: {capability}"
        )
    return True


def assert_identity_owns_task(identity_id, task, identity_field):
    expected = task.get(identity_field)
    if expected != identity_id:
        raise PermissionError(
            f"identity {identity_id} does not match task {identity_field}: {expected}"
        )
    return True
