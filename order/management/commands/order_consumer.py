"""order-consumer — applies payment results to orders.

payment.succeeded → mark order CONFIRMED and emit order.confirmed.
payment.failed    → mark order PAYMENT_FAILED.
Idempotent via ProcessedEvent.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from order.consumers import run_consumer
from order.events import emit_event
from order.models import Order

logger = logging.getLogger(__name__)


def handle_payment_succeeded(payload: dict, _headers: dict) -> None:
    order_id = payload["order_id"]
    updated = Order.objects.filter(id=order_id).update(status=Order.Status.CONFIRMED)
    if not updated:
        logger.warning("payment.succeeded for unknown order %s", order_id)
        return
    order = Order.objects.get(id=order_id)
    emit_event(
        "order.confirmed", key=order_id,
        payload={
            "event_id": str(uuid.uuid4()),
            "order_id": order_id,
            "user_id": order.user_id,
            "confirmed_at": timezone.now().isoformat(),
        },
    )
    logger.info("order %s confirmed", order_id)


def handle_payment_failed(payload: dict, _headers: dict) -> None:
    order_id = payload["order_id"]
    Order.objects.filter(id=order_id).update(status=Order.Status.PAYMENT_FAILED)
    logger.info("order %s payment failed: %s", order_id, payload.get("reason"))


class Command(BaseCommand):
    help = "Consume payment.* and update order status."

    def handle(self, *args: Any, **opts: Any) -> None:
        run_consumer(
            group_id="order-consumer",
            handlers={
                "payment.succeeded": handle_payment_succeeded,
                "payment.failed": handle_payment_failed,
            },
        )
