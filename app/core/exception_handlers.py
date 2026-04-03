from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_trace_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, *, code: int, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=40404, status_code=status.HTTP_404_NOT_FOUND)


class LLMError(AppError):
    """大模型调用异常"""

    def __init__(self, message: str = "llm service error") -> None:
        super().__init__(message, code=50200, status_code=status.HTTP_502_BAD_GATEWAY)


class LLMTimeoutError(AppError):
    """大模型超时"""

    def __init__(self) -> None:
        super().__init__("llm request timeout", code=50400, status_code=status.HTTP_504_GATEWAY_TIMEOUT)


class RateLimitExceeded(AppError):
    def __init__(self) -> None:
        super().__init__(
            "rate limit exceeded, please try again later",
            code=42900,
            status_code=429,
        )


class ConcurrentRequestBlocked(AppError):
    def __init__(self) -> None:
        super().__init__(
            "another request is being processed in this session",
            code=42901,
            status_code=429,
        )


class DuplicateRequestError(AppError):
    def __init__(self) -> None:
        super().__init__("duplicate request", code=40901, status_code=409)


class SessionNotActiveError(AppError):
    def __init__(self, session_status: str) -> None:
        super().__init__(
            f"session is {session_status}, cannot send messages",
            code=40301,
            status_code=403,
        )


class ContentTooLongError(AppError):
    def __init__(self, max_length: int) -> None:
        super().__init__(
            f"message content exceeds maximum length of {max_length} characters",
            code=42201,
            status_code=422,
        )


def _error_payload(message: str, *, code: int) -> dict:
    return {
        "code": code,
        "message": message,
        "data": None,
        "trace_id": get_trace_id(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.message, code=exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("request validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_payload("validation error", code=42200),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("database error", code=50001),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(str(exc.detail), code=exc.status_code * 100),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("internal server error", code=50000),
        )
