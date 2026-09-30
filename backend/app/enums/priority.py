from enum import StrEnum


class Priority(StrEnum):
    """Task priority accepted by task create and patch payloads."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
