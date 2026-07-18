import uuid

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class LoggerMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to the context variables.

    Parameters
    ----------
    app: FastAPI
        The FastAPI application instance.
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Add request ID to the context variables.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_host=request.client.host if request.client else None,
            status_code=None,
            path=request.url.path,
            method=request.method,
        )
        response = await call_next(request)
        structlog.contextvars.bind_contextvars(status_code=response.status_code)
        response.headers["X-Request-ID"] = request_id
        return response
