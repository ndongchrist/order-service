import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Simulate Kong having validated a JWT and injected the user id."""
    return {"HTTP_X_USER_ID": "user-123", "HTTP_X_CORRELATION_ID": "test-corr-1"}
