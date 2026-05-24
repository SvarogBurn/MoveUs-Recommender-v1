from django.db.models import QuerySet

from shared.errors.mu_error import MUError, MUErrorCode

MAX_PAGE_SIZE = 100


def validate_pagination(start: int, end: int) -> None:
    if start < 0 or end <= start or end - start > MAX_PAGE_SIZE:
        raise MUError(MUErrorCode.INVALID_PAGINATION)


def apply_pagination(qs: QuerySet, start: int, end: int) -> QuerySet:
    validate_pagination(start, end)
    return qs[start:end]
