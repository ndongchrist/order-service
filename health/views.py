"""Health endpoints.

* liveness  (`/health/`)      — "is the process up?" Cheap, never touches deps,
                                 so a slow DB can't make k8s *kill* the pod.
* readiness (`/health/ready/`) — "should I get traffic?" Verifies the DB; on
                                 failure k8s removes the pod from the Service
                                 endpoints but leaves it running.
"""
from __future__ import annotations

from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def liveness(_request: Request) -> Response:
    return Response({"status": "ok"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def readiness(_request: Request) -> Response:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - report any dependency failure
        return Response({"status": "unavailable", "database": str(exc)}, status=503)
    return Response({"status": "ready"})
