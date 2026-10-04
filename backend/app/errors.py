from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    trace_id: str
    retryable: bool = False


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    trace_id = getattr(request.state, "trace_id", "unknown")
    body = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        trace_id=trace_id,
        retryable=exc.retryable,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())
