class CompatibilityError(ValueError):
    pass


def check_component_compatibility(component, compatibility):
    component_type = component["component_type"]
    protocol_version = component["board_protocol_version"]
    supported = compatibility["compatible"].get(component_type, [])
    if protocol_version not in supported:
        raise CompatibilityError(
            f"{component_type} protocol {protocol_version} is not compatible"
        )

    required = set(compatibility["minimum_required_capabilities"].get(component_type, []))
    actual = set(component.get("capabilities", []))
    missing = sorted(required - actual)
    if missing:
        raise CompatibilityError(
            f"{component_type} is missing required capabilities: {', '.join(missing)}"
        )
    return True

