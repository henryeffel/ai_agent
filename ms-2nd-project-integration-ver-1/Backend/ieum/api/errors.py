from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ieum.schemas.error import ErrorResponse


class ApiException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    403: {"model": ErrorResponse, "description": "Actor lacks the required role"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "State transition conflict or duplicate"},
    422: {"model": ErrorResponse, "description": "Validation or insufficient evidence"},
    502: {"model": ErrorResponse, "description": "LLM or tool provider failure"},
    504: {"model": ErrorResponse, "description": "Provider timeout"},
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException):
        return _response(
            exc.status_code,
            exc.code,
            exc.message,
            exc.retryable,
            exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        details = {
            "fields": [
                {
                    "location": ".".join(str(part) for part in error["loc"]),
                    "type": error["type"],
                }
                for error in exc.errors()
            ]
        }
        return _response(
            422,
            "validation_error",
            "요청 입력값이 올바르지 않습니다.",
            False,
            details,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return _response(
            exc.status_code,
            "http_error",
            str(exc.detail),
            False,
            {},
        )


def _response(status_code, code, message, retryable, details):
    body = ErrorResponse(
        error={
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details,
        }
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))
