import pytest

from order import clients, views
from order.management.commands.order_consumer import (
    handle_payment_failed,
    handle_payment_succeeded,
)
from order.models import Order, OutboxEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_services(monkeypatch):
    catalog = {
        "SKU-1": {"sku": "SKU-1", "name": "Thing", "price": "10.00", "stock": 5},
    }
    charges = []

    def fake_get_product(sku):
        if sku not in catalog:
            raise clients.ProductNotFound(sku)
        return catalog[sku]

    def fake_charge(order_id, user_id, amount, currency="USD"):
        charges.append((order_id, amount))
        return {"status": "SUCCEEDED"}

    monkeypatch.setattr(views.clients, "get_product", fake_get_product)
    monkeypatch.setattr(views.clients, "charge", fake_charge)
    return charges


def test_checkout_creates_order_and_emits_order_created(api, auth_headers, mock_services):
    resp = api.post(
        "/", {"items": [{"product_sku": "SKU-1", "quantity": 2}], "currency": "USD"},
        format="json", **auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_amount"] == "20.00"
    assert body["status"] == "PENDING"
    evt = OutboxEvent.objects.get(topic="order.created")
    assert evt.payload["items"][0]["product_id"] == "SKU-1"
    assert evt.payload["total_amount"] == "20.00"
    assert len(mock_services) == 1  # payment charge was initiated


def test_checkout_rejects_insufficient_stock(api, auth_headers, mock_services):
    resp = api.post(
        "/", {"items": [{"product_sku": "SKU-1", "quantity": 99}]},
        format="json", **auth_headers,
    )
    assert resp.status_code == 400
    assert Order.objects.count() == 0


def test_checkout_requires_auth(api):
    assert api.post("/", {"items": [{"product_sku": "X", "quantity": 1}]}, format="json").status_code == 401


def test_payment_succeeded_confirms_and_emits_order_confirmed(auth_headers):
    order = Order.objects.create(user_id="u1", total_amount="10.00")
    handle_payment_succeeded({"order_id": str(order.id)}, {})
    order.refresh_from_db()
    assert order.status == Order.Status.CONFIRMED
    assert OutboxEvent.objects.filter(topic="order.confirmed").count() == 1


def test_payment_failed_marks_order_failed():
    order = Order.objects.create(user_id="u1", total_amount="10.00")
    handle_payment_failed({"order_id": str(order.id), "reason": "declined"}, {})
    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED
