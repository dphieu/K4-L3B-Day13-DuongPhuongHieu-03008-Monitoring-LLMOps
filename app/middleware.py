from __future__ import annotations

import time
import uuid
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Context variables are task-local, but clearing them is still important
        # for workers which serve more than one request during their lifetime.
        clear_contextvars()

        request_id = request.headers.get("x-request-id", "").strip().lower()
        correlation_id = (
            request_id
            if re.fullmatch(r"req-[0-9a-f]{8}", request_id)
            else f"req-{uuid.uuid4().hex[:8]}"
        )
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(
                round((time.perf_counter() - start) * 1000, 2)
            )
            return response
        finally:
            # Do not leave request metadata attached to a subsequent request.
            clear_contextvars()
