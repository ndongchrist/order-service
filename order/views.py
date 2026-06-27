"""Domain API views.

Ships with one authenticated `whoami` endpoint so the generated service runs
end-to-end (and tests pass) before you add real logic. Replace freely.
"""
from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def whoami(request: Request) -> Response:
    """Echo the gateway-verified user id — proves the trust boundary works."""
    return Response(
        {
            "service": "order-service",
            "user_id": getattr(request.user, "id", None),
            "correlation_id": getattr(request, "correlation_id", None),
        }
    )
