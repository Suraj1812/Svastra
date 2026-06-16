import time
from uuid import uuid4

from fastapi import Request

from app.core.logging import logger


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
    return response
