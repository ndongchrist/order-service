"""Cross-cutting request middleware shared by every service.

* CorrelationIdMiddleware — read (or mint) the trace id Kong injects, expose it
  on the request and in a contextvar so logs and Kafka headers can carry it.
* TrustedUserMiddleware — trust the `X-User-Id` header *only* because the
  default-deny NetworkPolicy means the request can only have come from Kong,
  which strips any client-sent value and re-injects the JWT-verified id.
"""
from __future__ import annotations

import contextvars
import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

CORRELATION_HEADER = "HTTP_X_CORRELATION_ID"
USER_ID_HEADER = "HTTP_X_USER_ID"

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        cid = request.META.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.correlation_id = cid  # type: ignore[attr-defined]
        token = _correlation_id.set(cid)
        try:
            response = self.get_response(request)
        finally:
            _correlation_id.reset(token)
        response["X-Correlation-Id"] = cid
        return response


class TrustedUserMiddleware:
    """Populate request.user_id from the gateway-injected header."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.user_id = request.META.get(USER_ID_HEADER)  # type: ignore[attr-defined]
        return self.get_response(request)


class CorrelationIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True
