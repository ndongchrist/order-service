from django.urls import path

from . import views

# Kong routes /orders/* here with strip_path, so paths are relative to root.
urlpatterns = [
    path("", views.orders, name="orders"),
    path("<uuid:order_id>/", views.order_detail, name="order-detail"),
]
