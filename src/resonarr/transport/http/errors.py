from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from resonarr.app.read_model_errors import SnapshotUnavailableError
from resonarr.transport.http.schemas.common import (
    ErrorDetailModel,
    ErrorResponseModel,
)


def _error_payload(*, code, message, details=None):
    payload = ErrorResponseModel(
        status="failed",
        error=ErrorDetailModel(
            code=code,
            message=message,
            details=details,
        ),
    )
    return payload.dict()


def install_exception_handlers(app: FastAPI):
    @app.exception_handler(SnapshotUnavailableError)
    async def handle_snapshot_unavailable(request: Request, exc: SnapshotUnavailableError):
        return JSONResponse(
            status_code=503,
            content=_error_payload(
                code="snapshot_unavailable",
                message=str(exc),
                details=exc.to_details(),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content=_error_payload(
                code="invalid_request",
                message="Invalid request parameters",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"

        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code=code,
                message=str(exc.detail),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="internal_error",
                message="Unhandled server error",
            ),
        )
