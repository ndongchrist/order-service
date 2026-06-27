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

