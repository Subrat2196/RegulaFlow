from typing import Generic, TypeVar

from pydantic import BaseModel

# TypeVar is a placeholder that says "this type will be decided later,
# by whoever uses this class." T can be any type — RegulationDocument,
# list[Gap], str — the wrapper works the same regardless.
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard envelope for every successful API response.

    Instead of returning raw data directly, every endpoint wraps its
    result in this envelope. This gives API consumers a consistent
    shape to work with — they always know to look at `data`, always
    know `success` tells them if it worked.

    Examples:
        APIResponse[RegulationDocument]   — a single regulation
        APIResponse[list[ComplianceGap]]  — a list of gaps
        APIResponse[str]                  — a simple message
    """

    success: bool = True
    data: T | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    """
    Standard envelope for every error response.

    When something goes wrong, every endpoint returns this shape.
    API consumers never have to guess what an error looks like.
    """

    success: bool = False
    error: str           # short machine-readable label, e.g. "regulation_not_found"
    detail: str | None = None  # longer human-readable explanation


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard envelope for list endpoints that return many items.

    Rather than returning every record at once (which breaks at scale),
    list endpoints return one page at a time. The consumer uses `total`,
    `page`, and `page_size` to know how many pages exist and request the next.
    """

    success: bool = True
    data: list[T]
    total: int       # total number of records across all pages
    page: int        # current page number (1-indexed)
    page_size: int   # how many records per page
