from fastapi import Header

from app.exceptions import PreconditionRequired, ValidationFailed


def get_if_match_version(
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> int:
    """Parse the If-Match header carrying the expected task version.

    Accepts the bare version as well as quoted and weak ETag forms.

    Args:
        if_match: raw header value sent by the client.

    Returns:
        int: expected task version.

    Raises:
        PreconditionRequired: when the header is missing.
        ValidationFailed: when the value is not a positive integer.
    """
    if if_match is None:
        raise PreconditionRequired()

    value = if_match.strip()
    if value.startswith("W/"):
        value = value[2:].strip()
    value = value.strip('"')

    try:
        version = int(value)
    except ValueError:
        raise ValidationFailed("If-Match must contain a task version") from None
    if version < 1:
        raise ValidationFailed("If-Match must contain a task version")
    return version
