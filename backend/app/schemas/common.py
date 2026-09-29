from typing import Annotated, Any, Collection, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

from app.exceptions import ValidationFailed

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PageParams:
    """Pagination request parameters shared by collection endpoints."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    ):
        """Validate page and page_size query parameters.

        Args:
            page: 1-based page number, must be at least 1.
            page_size: items per page, limited to MAX_PAGE_SIZE.

        Raises:
            ValidationFailed: when a value is outside the allowed range.
        """
        if page < 1:
            raise ValidationFailed("page must be >= 1")
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValidationFailed(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Return number of rows to skip for the current page."""
        return (self.page - 1) * self.page_size


class Paginated(BaseModel, Generic[T]):
    """Uniform envelope for paginated collections."""

    items: list[T]
    page: int
    page_size: int
    total: int


class PatchSchema(BaseModel):
    """Base for PATCH payloads following JSON Merge Patch semantics."""

    model_config = ConfigDict(extra="forbid")

    def changes(self) -> dict[str, Any]:
        """Return fields explicitly sent by the client.

        Omitted fields are left untouched, explicit null clears a nullable
        field.

        Returns:
            dict[str, Any]: mapping of sent fields to their values.
        """
        return self.model_dump(exclude_unset=True)


def check_sort(
    sort: str | None,
    allowed: Collection[str],
    default: str,
) -> str:
    """Validate a sort parameter against a per-collection whitelist.

    Args:
        sort: sort key as sent by the client, optional "-" prefix for desc.
        allowed: sort keys supported by the collection.
        default: key returned when the client sent nothing.

    Returns:
        str: validated sort key with direction prefix preserved.

    Raises:
        ValidationFailed: when sort is not in the whitelist.
    """
    if sort is None:
        return default
    field = sort[1:] if sort.startswith("-") else sort
    if field not in allowed:
        raise ValidationFailed(f"Unsupported sort field: {field}")
    return sort