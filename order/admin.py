from django.contrib import admin

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "status", "attempts", "created_at", "published_at")
    list_filter = ("status", "topic")
    search_fields = ("id", "topic", "correlation_id")
