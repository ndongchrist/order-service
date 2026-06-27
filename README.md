# order-service

A Django REST Framework microservice

Generated from [`service-template`](../service-template). Structurally identical
to every other service: DRF app, multi-stage Dockerfile, Helm `chart/`, CI.

## Layout

| Path | What |
|---|---|
| `config/` | Django project (settings, urls, middleware: correlation-id + trusted-user) |
| `health/` | `/health/` liveness, `/health/ready/` readiness (DB) |
| `order/` | Domain app + transactional **outbox** (`OutboxEvent`, `emit_event`, `relay_outbox`) |
| `chart/` | Helm chart: Deployment, Service, ConfigMap, HPA, ServiceMonitor, migrate hook, relay |
| `.github/workflows/ci.yml` | ruff → mypy → pytest → trivy → build/push (git SHA) → bump tag in `infra` |

## Local dev

```bash
uv sync --all-extras
cp .env.example .env          # USE_SQLITE=true for a zero-dependency loop
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest
```

## Events (transactional outbox)

```python
from django.db import transaction
from order.events import emit_event

with transaction.atomic():
    obj = MyModel.objects.create(...)
    emit_event("some.topic", key=str(obj.id), payload={...})
# the relay_outbox Deployment publishes it to Kafka after commit
```
