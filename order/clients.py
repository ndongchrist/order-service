"""REST clients for the services order-service talks to synchronously, over
ClusterIP DNS. Base URLs come from the ConfigMap (the Service name is the
contract). Correlation id is propagated for tracing.
"""
from __future__ import annotations

import os

import requests

from config.middleware import get_correlation_id

CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog-service")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "http://payment-service")
TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "3"))


class ProductNotFound(Exception):
    pass


def _headers() -> dict:
    return {"X-Correlation-Id": get_correlation_id()}


def get_product(sku: str) -> dict:
    resp = requests.get(f"{CATALOG_URL}/products/{sku}/", headers=_headers(), timeout=TIMEOUT)
    if resp.status_code == 404:
        raise ProductNotFound(sku)
    resp.raise_for_status()
    return resp.json()


def charge(order_id: str, user_id: str, amount: str, currency: str = "USD") -> dict:
    """Initiate payment. The authoritative result arrives async via the
    payment.succeeded / payment.failed events; this just kicks it off."""
    resp = requests.post(
        f"{PAYMENT_URL}/charge/",
        json={"order_id": order_id, "user_id": user_id, "amount": amount, "currency": currency},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
