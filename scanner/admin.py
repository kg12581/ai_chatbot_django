from django.contrib import admin

from .models import ScanRun, SecretFinding


@admin.register(ScanRun)
class ScanRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "files_scanned", "findings_count", "duration_ms", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(SecretFinding)
class SecretFindingAdmin(admin.ModelAdmin):
    list_display = ("rule_name", "severity", "file_path", "line_number", "secret_preview", "entropy", "status", "created_at")
    list_filter = ("severity", "status", "rule_id")
    search_fields = ("file_path", "rule_name", "secret_preview")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
