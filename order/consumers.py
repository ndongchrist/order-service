"""Kafka consumer runtime shared by this service's consumer commands.

`run_consumer` owns the poll loop, JSON decoding, correlation-id propagation,
idempotency (via ProcessedEvent), and manual offset commits — so each consumer
command only has to supply a per-topic handler.
"""
from __future__ import annotations

import json
import logging
import signal
from collections.abc import Callable

from django.db import transaction

from config.middleware import _correlation_id

from .events import build_consumer
from .models import ProcessedEvent

logger = logging.getLogger(__name__)

Handler = Callable[[dict, dict], None]


def _headers_to_dict(raw) -> dict:
    out: dict[str, str] = {}
    for key, value in raw or []:
        out[key] = value.decode() if isinstance(value, bytes | bytearray) else str(value)
    return out


def run_consumer(group_id: str, handlers: dict[str, Handler]) -> None:
    """Consume the given topics, dispatching each message to handlers[topic].

    At-least-once + idempotent: a message whose event_id is already in
    ProcessedEvent is skipped. Offsets are committed only after the handler and
    the ProcessedEvent insert commit together.
    """
    consumer = build_consumer(group_id, list(handlers))
    running = {"flag": True}
    signal.signal(signal.SIGTERM, lambda *_: running.update(flag=False))
    signal.signal(signal.SIGINT, lambda *_: running.update(flag=False))
    logger.info("consumer %s started on %s", group_id, list(handlers))

    try:
        while running["flag"]:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error("consumer error: %s", msg.error())
                continue

            headers = _headers_to_dict(msg.headers())
            token = _correlation_id.set(headers.get("correlation_id", "-"))
            try:
                payload = json.loads(msg.value().decode())
                event_id = payload.get("event_id") or f"{msg.topic()}-{msg.offset()}"
                handler = handlers[msg.topic()]
                _process_once(msg.topic(), event_id, payload, headers, handler)
                consumer.commit(msg)  # advance only after successful handling
            except Exception:  # noqa: BLE001 - never crash the loop on one bad message
                logger.exception("failed handling %s offset %s", msg.topic(), msg.offset())
            finally:
                _correlation_id.reset(token)
    finally:
        consumer.close()
        logger.info("consumer %s stopped", group_id)


def _process_once(topic: str, event_id: str, payload: dict, headers: dict, handler: Handler) -> None:
    with transaction.atomic():
        _, created = ProcessedEvent.objects.get_or_create(
            event_id=event_id, defaults={"topic": topic}
        )
        if not created:
            logger.info("skipping duplicate %s %s", topic, event_id)
            return
        handler(payload, headers)
