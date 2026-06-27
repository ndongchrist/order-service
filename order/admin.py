from django.contrib import admin

from .models import Order, OrderItem, OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "status", "attempts", "created_at", "published_at")
    list_filter = ("status", "topic")
    search_fields = ("id", "topic", "correlation_id")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "user_id")
    inlines = [OrderItemInline]
