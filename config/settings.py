"""Django settings for order-service.

Twelve-factor: every deployment-specific value comes from the environment.
Defaults here are safe for local/dev only; prod values are injected via the
Helm ConfigMap and Sealed Secrets in the `infra` repo.
"""
from __future__ import annotations

from pathlib import Path

from environs import Env

env = Env()
env.read_env()  # picks up a local .env if present; no-op in the cluster

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core -------------------------------------------------------------------
SECRET_KEY = env.str("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", ["*"])
# Behind Kong + ClusterIP we terminate TLS at the edge; trust the forwarded proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

SERVICE_NAME = "order-service"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_prometheus",
    "health",
    "order",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "config.middleware.CorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.middleware.TrustedUserMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

# --- Database (one Postgres per service) ------------------------------------
# USE_SQLITE is a dev/inner-loop convenience (Phase 2, before CloudNativePG
# exists). Production and the cluster always use Postgres.
if env.bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django_prometheus.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django_prometheus.db.backends.postgresql",
            "NAME": env.str("POSTGRES_DB", "order"),
            "USER": env.str("POSTGRES_USER", "order"),
            "PASSWORD": env.str("POSTGRES_PASSWORD", "order"),
            "HOST": env.str("POSTGRES_HOST", "localhost"),
            "PORT": env.int("POSTGRES_PORT", 5432),
            "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", 60),
        }
    }

# --- DRF + auth -------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "order.auth.GatewayUserAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "order-service",
    "DESCRIPTION": "A Django REST Framework microservice",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Kafka (event backbone) -------------------------------------------------
KAFKA_BOOTSTRAP_SERVERS = env.str("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SCHEMA_REGISTRY_URL = env.str("SCHEMA_REGISTRY_URL", "http://localhost:8080/apis/registry/v2")

# --- i18n / static ----------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Structured logging (JSON, correlation-id aware) ------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "filters": {
        "correlation": {"()": "config.middleware.CorrelationIdLogFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["correlation"],
        }
    },
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", "INFO")},
}
