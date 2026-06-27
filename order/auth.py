"""Authentication that trusts the gateway-verified identity.

Kong validates the JWT at the edge and injects `X-User-Id`. Downstream services
never re-validate the token — they trust the header because the default-deny
NetworkPolicy guarantees the only ingress is Kong. This class turns that header
into a DRF-authenticated principal.
"""
from __future__ import annotations

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request


class GatewayUser:
    """Minimal authenticated principal — no DB row, just the verified id."""

    is_authenticated = True

    def __init__(self, user_id: str) -> None:
        self.id = user_id
        self.pk = user_id

    def __str__(self) -> str:
        return f"GatewayUser({self.id})"


class GatewayUserAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[GatewayUser, None] | None:
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return None  # anonymous; IsAuthenticated will 401
        return GatewayUser(str(user_id)), None

    def authenticate_header(self, request: Request) -> str:
        # Presence of this makes DRF return 401 (not 403) for anonymous requests.
        return "Gateway"
