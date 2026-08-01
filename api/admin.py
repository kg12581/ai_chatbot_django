from django.contrib import admin

from .models import DouyinHotSearch, SchedulerConfig


@admin.register(DouyinHotSearch)
class DouyinHotSearchAdmin(admin.ModelAdmin):
    list_display = ("rank", "title", "hot_value", "label", "crawl_batch", "created_at")
    list_display_links = ("title",)
    list_filter = ("label", "crawl_batch")
    search_fields = ("title",)
    date_hierarchy = "crawl_batch"
    ordering = ("rank",)


@admin.register(SchedulerConfig)
class SchedulerConfigAdmin(admin.ModelAdmin):
    list_display = ("task_name", "cron_expr", "enabled", "last_run_at", "run_count", "updated_at")
    list_display_links = ("task_name",)
    list_filter = ("enabled",)
    search_fields = ("task_name", "task_id")
    list_editable = ("enabled", "cron_expr")
    readonly_fields = ("last_run_at", "last_run_result", "run_count", "created_at", "updated_at")
