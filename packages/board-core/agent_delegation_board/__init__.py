from .compatibility import CompatibilityError, check_component_compatibility
from .events import EVENT_TYPES, is_known_event_type
from .lifecycle import BoardLifecycleError
from .permissions import (
    PermissionError,
    assert_identity_owns_task,
    check_identity_capability,
    check_role_capability,
)
from .state_machine import StateTransitionError, transition
from .task_identity import generate_task_id
from .validation import (
    ProtocolValidationError,
    validate_event,
    validate_identity,
    validate_task,
)

__all__ = [
    "CompatibilityError",
    "EVENT_TYPES",
    "BoardLifecycleError",
    "PermissionError",
    "ProtocolValidationError",
    "StateTransitionError",
    "assert_identity_owns_task",
    "check_component_compatibility",
    "check_identity_capability",
    "check_role_capability",
    "generate_task_id",
    "is_known_event_type",
    "transition",
    "validate_event",
    "validate_identity",
    "validate_task",
]
