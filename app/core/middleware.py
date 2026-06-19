from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.core.logging import logger
from app.core.responses import error_response


class RequestBodyTooLargeError(ValueError):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("state", {}).get("request_id")
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        declared_length = headers.get(b"content-length")
        if declared_length is not None:
            try:
                parsed_length = int(declared_length)
            except ValueError:
                response = JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "BAD_REQUEST",
                        "Content-Length header must be a valid integer",
                        request_id=request_id,
                    ),
                )
                await response(scope, receive, send)
                return
            if parsed_length < 0:
                response = JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "BAD_REQUEST",
                        "Content-Length header must be a valid integer",
                        request_id=request_id,
                    ),
                )
                await response(scope, receive, send)
                return
            if parsed_length > self.max_bytes:
                response = _payload_too_large_response(request_id=request_id)
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_bytes:
                    raise RequestBodyTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLargeError:
            response = _payload_too_large_response(request_id=request_id)
            await response(scope, receive, send)


def _apply_security_headers(response, *, elapsed_ms: float):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    return response


def _payload_too_large_response(*, request_id: str | None):
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content=error_response(
            "PAYLOAD_TOO_LARGE",
            f"Request body exceeds the {settings.max_request_bytes}-byte limit",
            request_id=request_id,
        ),
    )


async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()

    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

    logger.info(
        "request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Request-ID"] = request_id
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return _apply_security_headers(response, elapsed_ms=elapsed_ms)
