"""Outbox relay — runs as its own Deployment, not in the web pods.

Polls PENDING OutboxEvent rows, publishes each to Kafka with the correlation id
as a header, and marks it PUBLISHED only after the broker acks. At-least-once by
design; consumers must be idempotent.
"""
from __future__ import annotations

import json
import signal
import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from order.events import build_producer
from order.models import OutboxEvent


class Command(BaseCommand):
    help = "Publish pending outbox events to Kafka."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--poll-interval", type=float, default=1.0)

    def handle(self, *args: Any, **opts: Any) -> None:
        producer = build_producer()
        running = {"flag": True}
        signal.signal(signal.SIGTERM, lambda *_: running.update(flag=False))
        signal.signal(signal.SIGINT, lambda *_: running.update(flag=False))
        self.stdout.write("outbox relay started")

        while running["flag"]:
            published = self._drain(producer, opts["batch_size"])
            if published == 0:
                time.sleep(opts["poll_interval"])
        producer.flush(10)
        self.stdout.write("outbox relay stopped")

    def _drain(self, producer: Any, batch_size: int) -> int:
        # select_for_update(skip_locked) lets multiple relay replicas run safely.
        with transaction.atomic():
            rows = list(
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(status=OutboxEvent.Status.PENDING)
                .order_by("created_at")[:batch_size]
            )
            for event in rows:
                headers = [("correlation_id", event.correlation_id.encode())]
                headers += [
                    ("schema_version", str(event.schema_version).encode()),
                ]
                headers += [(k, str(v).encode()) for k, v in (event.headers or {}).items()]
                try:
                    producer.produce(
                        topic=event.topic,
                        key=event.key.encode() if event.key else None,
                        value=json.dumps(event.payload).encode(),
                        headers=headers,
                    )
                    producer.flush(10)
                    event.status = OutboxEvent.Status.PUBLISHED
                    event.published_at = timezone.now()
                except Exception as exc:  # noqa: BLE001
                    event.status = OutboxEvent.Status.FAILED
                    event.last_error = str(exc)
                event.attempts += 1
                event.save(update_fields=["status", "published_at", "attempts", "last_error"])
        return len(rows)
