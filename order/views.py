"""Order API — the checkout coordinator.

POST /  (checkout):
  1. validate every line against catalog (stock + price snapshot) over REST
  2. in ONE transaction: create the Order + items AND write the order.created
     outbox event (catalog-consumer decrements stock from it)
  3. after commit: REST-charge payment-service to kick off the payment
The payment *result* arrives asynchronously (payment.succeeded/failed) and is
applied by order-consumer — see the management commands.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from . import clients
from .events import emit_event
from .models import Order, OrderItem
from .serializers import CheckoutSerializer, OrderSerializer

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
def orders(request: Request) -> Response:
    if request.method == "GET":
        qs = Order.objects.filter(user_id=request.user.id).prefetch_related("items")
        return Response(OrderSerializer(qs, many=True).data)
    return _checkout(request)


def _checkout(request: Request) -> Response:
    req = CheckoutSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    user_id = request.user.id
    currency = req.validated_data["currency"]

    # 1. Validate + snapshot against catalog.
    lines = []
    total = Decimal("0.00")
    for item in req.validated_data["items"]:
        sku, qty = item["product_sku"], item["quantity"]
        try:
            product = clients.get_product(sku)
        except clients.ProductNotFound:
            return Response({"detail": f"unknown product {sku}"}, status=400)
        if product["stock"] < qty:
            return Response({"detail": f"insufficient stock for {sku}"}, status=400)
        price = Decimal(str(product["price"]))
        total += price * qty
        lines.append({"sku": sku, "name": product["name"], "price": price, "qty": qty})

    # 2. Persist order + outbox event atomically.
    with transaction.atomic():
        order = Order.objects.create(user_id=user_id, total_amount=total, currency=currency)
        OrderItem.objects.bulk_create(
            OrderItem(order=order, product_sku=ln["sku"], name=ln["name"],
                      unit_price=ln["price"], quantity=ln["qty"])
            for ln in lines
        )
        emit_event(
            "order.created", key=str(order.id),
            payload={
                "event_id": str(uuid.uuid4()),
                "order_id": str(order.id),
                "user_id": user_id,
                "items": [
                    {"product_id": ln["sku"], "quantity": ln["qty"], "unit_price": str(ln["price"])}
                    for ln in lines
                ],
                "total_amount": str(total),
                "currency": currency,
                "created_at": timezone.now().isoformat(),
            },
        )

    # 3. Kick off payment (best-effort; result comes back async).
    try:
        clients.charge(str(order.id), user_id, str(total), currency)
    except Exception:  # noqa: BLE001 - order stays PENDING; a real system retries
        logger.exception("charge initiation failed for order %s", order.id)

    return Response(OrderSerializer(order).data, status=201)


@api_view(["GET"])
def order_detail(request: Request, order_id: str) -> Response:
    try:
        order = Order.objects.prefetch_related("items").get(id=order_id, user_id=request.user.id)
    except Order.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    return Response(OrderSerializer(order).data)
