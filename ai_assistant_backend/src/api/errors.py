from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status


@dataclass
class AppError(Exception):
    """Application error with stable error code and HTTP status."""

    code: str
    message: str
    http_status: int = status.HTTP_400_BAD_REQUEST
    details: dict[str, Any] | None = None


# PUBLIC_INTERFACE
def install_exception_handlers(app) -> None:
    """Register exception handlers on a FastAPI app.

    Args:
        app: FastAPI app instance.

    Returns:
        None
    """

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Convert Pydantic validation into a stable API error shape.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "ok": False,
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": {"errors": exc.errors()},
                },
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Avoid leaking internals. Logs would go here in a real deployment.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": "Unexpected server error.",
                    "details": None,
                },
            },
        )
