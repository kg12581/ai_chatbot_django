from django.conf import settings
from django.db import models


class Conversation(models.Model):
    title = models.CharField(max_length=200, default="新对话")
    # 所属用户：null=True 用于兼容历史数据（迁移时归属到 admin）
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"#{self.id} {self.title}"

    @property
    def message_count(self):
        return self.messages.count()


class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "用户"),
        ("assistant", "助手"),
    ]
    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


# MCP 与 Skill 模型
from .mcp_models import McpServer, McpTool, Skill  # noqa: E402,F401

# 硬编码扫描模型
from .scanner_models import ScanRun, SecretFinding  # noqa: E402,F401

# 埋点统计模型
from .analytics_models import AnalyticsEvent  # noqa: E402,F401
