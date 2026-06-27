"""Outbox write helper + Kafka client factories.

`emit_event` is the only thing your views/services should call. Call it INSIDE
the same `transaction.atomic()` as your state change:

    with transaction.atomic():
        order = Order.objects.create(...)
        emit_event("order.created", key=str(order.id), payload={...})
"""
from __future__ import annotations

from typing import Any

from django.conf import settings

from config.middleware import get_correlation_id

from .models import OutboxEvent


def emit_event(
    topic: str,
    *,
    payload: dict[str, Any],
    key: str = "",
    schema_version: int = 1,
    headers: dict[str, str] | None = None,
) -> OutboxEvent:
    """Persist an event to the outbox (does NOT publish — the relay does)."""
    return OutboxEvent.objects.create(
        topic=topic,
        key=key,
        payload=payload,
        schema_version=schema_version,
        headers=headers or {},
        correlation_id=get_correlation_id(),
    )


def build_producer():  # pragma: no cover - thin wrapper over confluent_kafka
    from confluent_kafka import Producer

    return Producer(
        {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "enable.idempotence": True,  # no duplicates on broker retries
            "acks": "all",
            "client.id": settings.SERVICE_NAME,
        }
    )


def build_consumer(group_id: str, topics: list[str]):  # pragma: no cover
    from confluent_kafka import Consumer

    consumer = Consumer(
        {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "enable.auto.commit": False,  # commit only after successful handling
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe(topics)
    return consumer
