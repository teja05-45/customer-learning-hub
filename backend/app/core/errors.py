"""Domain exceptions and the single API error envelope.

Every failure the UI needs to explain (missing provenance, unsupported status
transition, demo-data guard rail) is raised as an AppError so the client always
receives ``{"error": {"code", "message", "details"}}``.
"""

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details: Any | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_error"


class RuleViolationError(AppError):
    """A business rule blocked the request (e.g. invalid status transition)."""

    status_code = 400
    code = "rule_violation"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
