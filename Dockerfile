# syntax=docker/dockerfile:1.7
# ---- Stage 1: build a self-contained virtualenv with uv -------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
# Resolve deps first (cache layer); only re-runs when the lockfile changes.
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ---- Stage 2: slim runtime, no build tools, non-root ----------------------
FROM python:3.12-slim AS runtime

# libpq for psycopg; tini for correct PID-1 signal handling.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --home /app app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

RUN python manage.py collectstatic --noinput || true

USER 10001
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--threads", "2", \
     "--access-logfile", "-", "--error-logfile", "-"]
