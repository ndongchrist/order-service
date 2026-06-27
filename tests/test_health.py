import pytest


def test_liveness_is_open(api):
    resp = api.get("/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.django_db
def test_readiness_checks_db(api):
    resp = api.get("/health/ready/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_whoami_requires_gateway_header(api):
    assert api.get("/whoami/").status_code == 401


def test_whoami_trusts_gateway_user(api, auth_headers):
    resp = api.get("/whoami/", **auth_headers)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user-123"
