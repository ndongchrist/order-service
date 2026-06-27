"""notification-consumer — would send emails/SMS; here it logs.

Listens for order.confirmed and payment.failed. Separate consumer group from
order-consumer, so both independently receive payment.failed.
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand

from order.consumers import run_consumer

logger = logging.getLogger(__name__)


def notify_order_confirmed(payload: dict, _headers: dict) -> None:
    logger.info("NOTIFY user=%s: your order %s is confirmed 🎉",
                payload.get("user_id"), payload.get("order_id"))


def notify_payment_failed(payload: dict, _headers: dict) -> None:
    logger.info("NOTIFY user=%s: payment for order %s failed (%s)",
                payload.get("user_id"), payload.get("order_id"), payload.get("reason"))


class Command(BaseCommand):
    help = "Consume order.confirmed and payment.failed and notify the user."

    def handle(self, *args: Any, **opts: Any) -> None:
        run_consumer(
            group_id="notification-consumer",
            handlers={
                "order.confirmed": notify_order_confirmed,
                "payment.failed": notify_payment_failed,
            },
        )
