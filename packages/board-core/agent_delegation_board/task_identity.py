from datetime import datetime, timezone
import secrets


def generate_task_id(now=None, random_suffix=None):
    """Return a board-owned, time-sortable, filesystem-safe task id."""
    timestamp = now or datetime.now(timezone.utc)
    stamp = timestamp.strftime("%Y%m%dT%H%M%S")
    millis = int(timestamp.microsecond / 1000)
    suffix = random_suffix or _random_suffix()
    return f"aq_{stamp}{millis:03d}Z_{suffix}"


def _random_suffix():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(4))
