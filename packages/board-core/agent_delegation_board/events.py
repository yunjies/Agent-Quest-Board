EVENT_TYPES = {
    "task_published",
    "task_amended",
    "task_cancelled",
    "task_claimed",
    "task_accepted",
    "execution_started",
    "result_submitted",
    "review_requested",
    "review_approved",
    "review_rejected",
    "revision_requested",
    "revision_submitted",
    "clarification_requested",
    "blocked",
    "status_changed",
    "permission_denied",
    "component_incompatible",
    "incident_created",
    "task_closed",
}


def is_known_event_type(event_type):
    return event_type in EVENT_TYPES
