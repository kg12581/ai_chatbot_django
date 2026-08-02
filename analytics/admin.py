from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "event_name", "page_url", "user", "session_key", "ip", "created_at")
    list_filter = ("event_type", "event_name", "created_at")
    search_fields = ("event_name", "page_url", "session_key")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
