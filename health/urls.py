from django.urls import path

from . import views

urlpatterns = [
    path("", views.liveness, name="liveness"),
    path("ready/", views.readiness, name="readiness"),
]
