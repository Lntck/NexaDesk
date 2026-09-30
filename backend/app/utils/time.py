from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC timestamp used for entity bookkeeping.

    Returns:
        datetime: timezone-aware current timestamp.
    """
    return datetime.now(UTC)
