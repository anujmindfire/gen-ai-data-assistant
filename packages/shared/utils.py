"""Shared utility functions across monorepo packages."""

import uuid
from datetime import UTC, datetime


def generate_uuid() -> str:
    """Generate a string representation of a UUIDv4."""
    return str(uuid.uuid4())


def get_utc_now() -> str:
    """Get current UTC timestamp formatted as ISO-8601 string."""
    return datetime.now(UTC).isoformat()
