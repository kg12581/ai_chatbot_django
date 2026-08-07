from django.contrib import admin

from .models import Conversation, Message, McpServer, McpTool, Skill, ScanRun, SecretFinding, AnalyticsEvent


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "message_count", "created_at", "updated_at")
    list_display_links = ("id", "title")
    search_fields = ("title", "user__username")
    list_filter = ("user", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-updated_at",)

    @admin.display(description="消息数")
    def message_count(self, obj):
        return obj.message_count


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "content_preview", "created_at")
    list_display_links = ("id",)
    list_filter = ("role", "created_at")
    search_fields = ("content",)
    date_hierarchy = "created_at"
    raw_id_fields = ("conversation",)
    ordering = ("-created_at",)

    @admin.display(description="内容预览")
    def content_preview(self, obj):
        return obj.content[:80] + ("..." if len(obj.content) > 80 else "")


# ==================== MCP 与 Skill 管理 ====================


@admin.register(McpServer)
class McpServerAdmin(admin.ModelAdmin):
    list_display = ("name", "transport", "enabled", "description", "updated_at")
    list_display_links = ("name",)
    list_filter = ("transport", "enabled")
    search_fields = ("name", "description", "command", "url")
    ordering = ("-created_at",)


@admin.register(McpTool)
class McpToolAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "enabled", "func_path", "updated_at")
    list_display_links = ("name",)
    list_filter = ("category", "enabled")
    search_fields = ("name", "description", "func_path")
    ordering = ("category", "name")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color", "is_active", "created_by", "updated_at")
    list_display_links = ("name",)
    list_filter = ("is_active", "color", "created_by")
    search_fields = ("name", "description", "system_prompt")
    ordering = ("-is_active", "-created_at")
    raw_id_fields = ("created_by",)
