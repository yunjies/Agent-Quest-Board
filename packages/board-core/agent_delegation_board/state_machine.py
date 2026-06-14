class StateTransitionError(ValueError):
    pass


TRANSITIONS = {
    "draft": {"published", "needs_user_action", "failed"},
    "published": {"accepted_by_contractor", "needs_user_action", "failed"},
    "accepted_by_contractor": {"running", "needs_user_action", "failed"},
    "running": {"submitted", "needs_user_action", "failed"},
    "submitted": {"reviewing", "needs_user_action", "failed"},
    "reviewing": {"approved", "rejected", "needs_user_action", "failed"},
    "approved": {"closed"},
    "rejected": {"revision_requested"},
    "revision_requested": {"running", "needs_user_action", "failed"},
    "needs_user_action": {"published", "running", "reviewing", "failed"},
    "failed": {"revision_requested", "needs_user_action"},
    "closed": set(),
}


def transition(current, target):
    allowed = TRANSITIONS.get(current)
    if allowed is None:
        raise StateTransitionError(f"Unknown state: {current}")
    if target not in allowed:
        raise StateTransitionError(f"Illegal transition: {current} -> {target}")
    return target

