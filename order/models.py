"""Domain models.

Ships with the transactional **outbox** table every service needs. Add your
domain models below it; write business rows and their OutboxEvent in the SAME
`transaction.atomic()` block so "state changed" and "event will publish" commit
or roll back together.
"""
from __future__ import annotations

import uuid

from django.db import models


class OutboxEvent(models.Model):
    """An event waiting to be published to Kafka.

    The relay (management command `relay_outbox`) polls PENDING rows, publishes
    them, and marks them PUBLISHED. Because the row is written in the same DB
    transaction as the state change, a crash can never leave the two out of sync.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PUBLISHED = "PUBLISHED"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255)
    key = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField()
    headers = models.JSONField(default=dict)
    schema_version = models.PositiveIntegerField(default=1)
    correlation_id = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        # Explicit name keeps the shipped migration identical across all services.
        indexes = [
            models.Index(fields=["status", "created_at"], name="outbox_status_created_idx")
        ]

    def __str__(self) -> str:
        return f"{self.topic}:{self.id} [{self.status}]"


# --- Add your domain models below -------------------------------------------
