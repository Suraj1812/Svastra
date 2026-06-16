from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.auth_service import RegistrationError
from app.core.logging import logger
from app.core.responses import error_response


def _request_id(request: Request):
    return getattr(request.state, "request_id", None)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, str(exc.detail), request_id=_request_id(request)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            "VALIDATION_ERROR",
            "Request validation failed",
            details=details,
            request_id=_request_id(request),
        ),
    )


async def registration_exception_handler(request: Request, exc: RegistrationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response("REGISTRATION_ERROR", str(exc), request_id=_request_id(request)),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred",
            request_id=_request_id(request),
        ),
    )
