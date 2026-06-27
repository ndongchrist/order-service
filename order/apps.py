from django.apps import AppConfig


class OrderConfig(AppConfig):
    name = "order"
    # Distinct label so a service named after a Django builtin (e.g. "auth")
    # doesn't collide with django.contrib.* app labels.
    label = "order_app"
