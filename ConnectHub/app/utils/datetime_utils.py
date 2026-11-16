from datetime import datetime, timezone


def utcnow() -> datetime:
    """Single source of truth for application timestamps (UTC, microseconds)."""
    return datetime.now(timezone.utc)
