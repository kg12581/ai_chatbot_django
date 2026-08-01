from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "message_count", "created_at", "updated_at")
    list_display_links = ("id", "title")
    search_fields = ("title",)
    list_filter = ("created_at",)
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
