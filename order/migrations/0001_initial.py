import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OutboxEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("topic", models.CharField(max_length=255)),
                ("key", models.CharField(blank=True, default="", max_length=255)),
                ("payload", models.JSONField()),
                ("headers", models.JSONField(default=dict)),
                ("schema_version", models.PositiveIntegerField(default=1)),
                ("correlation_id", models.CharField(blank=True, default="", max_length=64)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PUBLISHED", "Published"), ("FAILED", "Failed")], db_index=True, default="PENDING", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True, default="")),
            ],
            options={
                "ordering": ["created_at"],
                "indexes": [models.Index(fields=["status", "created_at"], name="outbox_status_created_idx")],
            },
        ),
    ]
