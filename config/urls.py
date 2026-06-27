"""Root URL configuration.

`/health/` and `/metrics` are infra endpoints (no auth). Everything else lives
under the service's own app router. Kong strips the `/order`
prefix before forwarding, so routes here are mounted at the root.
"""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("health/", include("health.urls")),
    path("", include("django_prometheus.urls")),  # exposes /metrics
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("", include("order.urls")),
]
