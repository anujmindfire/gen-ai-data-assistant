"""Shared utility functions across monorepo packages."""

from datetime import datetime, timezone
import uuid


def generate_uuid() -> str:
    """Generate a string representation of a UUIDv4."""
    return str(uuid.uuid4())


def get_utc_now() -> str:
    """Get current UTC timestamp formatted as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
