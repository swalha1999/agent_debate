"""Consistent error envelope + exception handlers (task 10.4, issue #71).

PRD §6: the API is a thin shell over the SDK, so every failure — a bad request,
an unknown ``run_id``, a server misconfiguration, an unexpected fault — must
return ONE consistent JSON shape rather than FastAPI's default ``{"detail": …}``
mixed with stray stack traces. The single envelope is::

    {"error": {"type": <machine label>, "message": <human text>, "detail": <extra>}}

``type`` is a stable machine label (a :class:`ErrorType` value, single source of
truth), ``message`` is safe human text and ``detail`` is optional structured
extra (e.g. the field-level validation errors) or ``None``.

Handlers are registered on the app via :func:`register_exception_handlers` in the
``create_app`` factory. They deliberately NEVER echo a secret or a stack trace:
domain errors with safe, authored messages pass their text through; the generic
:class:`Exception` handler returns a fixed safe message and logs the real fault
via the LOG package for operators. Every handled error is logged.
"""

from __future__ import annotations

from enum import StrEnum

from agent_debate.core.security import InvalidInputError
from agent_debate.core.validation import MissingApiKeyError
from agent_debate.log import get_logger
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

#: 422 status (non-deprecated spelling) for request-validation failures.
_HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT

#: Top-level key wrapping every error envelope (single source of truth).
ERROR_KEY = "error"

#: ``run_id`` namespacing this surface's structured error-log emissions.
_LOG_RUN_ID = "api.errors"

_LOG = get_logger(_LOG_RUN_ID)

#: Fixed, safe message for unexpected faults — never leaks internals.
_UNEXPECTED_MESSAGE = "An unexpected internal error occurred."

#: Safe message for a missing provider key — names the cause, never the key.
_MISSING_KEY_MESSAGE = "Server misconfigured: a required API key is missing."


class ErrorType(StrEnum):
    """Stable machine-readable ``type`` labels for the error envelope."""

    VALIDATION = "validation_error"
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"
    SERVER_MISCONFIGURED = "server_misconfigured"
    INTERNAL = "internal_error"


def _envelope(
    *, error_type: ErrorType, message: str, detail: object | None = None
) -> dict[str, object]:
    """Build the consistent ``{"error": {...}}`` body (single shape)."""
    return {ERROR_KEY: {"type": str(error_type), "message": message, "detail": detail}}


def _json_error(
    status_code: int, error_type: ErrorType, message: str, detail: object | None = None
) -> JSONResponse:
    """Return a :class:`JSONResponse` carrying the consistent error envelope."""
    return JSONResponse(
        status_code=status_code,
        content=_envelope(error_type=error_type, message=message, detail=detail),
    )


async def _handle_validation(request: Request, exc: Exception) -> JSONResponse:
    """Map a Pydantic/body validation failure to a 422 envelope (safe detail).

    ``jsonable_encoder`` makes the field-level errors JSON-safe — Pydantic may
    attach a raw exception object (e.g. our :class:`InvalidInputError`) in a
    rule's context, which is not natively serialisable.
    """
    raw = exc.errors() if isinstance(exc, RequestValidationError) else None
    detail = jsonable_encoder(raw, custom_encoder={Exception: str}) if raw else None
    _LOG.info("request_validation_failed", path=request.url.path)
    return _json_error(_HTTP_422, ErrorType.VALIDATION, "Request validation failed.", detail)


async def _handle_invalid_input(request: Request, exc: Exception) -> JSONResponse:
    """Map a 7.2 :class:`InvalidInputError` to a 422 with its safe message."""
    _LOG.info("invalid_input", path=request.url.path)
    return _json_error(_HTTP_422, ErrorType.INVALID_INPUT, str(exc))


async def _handle_missing_key(request: Request, exc: Exception) -> JSONResponse:
    """Map a :class:`MissingApiKeyError` to a safe 503 — never echo the key."""
    _LOG.error("missing_api_key", path=request.url.path)
    return _json_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorType.SERVER_MISCONFIGURED,
        _MISSING_KEY_MESSAGE,
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Re-wrap FastAPI/Starlette ``HTTPException`` in the consistent envelope."""
    assert isinstance(exc, StarletteHTTPException)
    error_type = (
        ErrorType.NOT_FOUND if exc.status_code == status.HTTP_404_NOT_FOUND else ErrorType.INTERNAL
    )
    _LOG.info("http_exception", path=request.url.path, status_code=exc.status_code)
    return _json_error(exc.status_code, error_type, str(exc.detail))


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort 500 — log the real fault, return a fixed safe message."""
    _LOG.error("unexpected_error", path=request.url.path, error_type=type(exc).__name__)
    return _json_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorType.INTERNAL, _UNEXPECTED_MESSAGE
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the consistent-envelope handlers on ``app`` (most→least specific)."""
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(InvalidInputError, _handle_invalid_input)
    app.add_exception_handler(MissingApiKeyError, _handle_missing_key)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected)


__all__ = ["ERROR_KEY", "ErrorType", "register_exception_handlers"]
