from django.contrib.auth.models import User
from django.db import models


class AnalyticsEvent(models.Model):
    """前端/后端埋点事件"""

    EVENT_TYPES = [
        ("pageview", "页面访问"),
        ("click", "点击"),
        ("action", "功能操作"),
        ("error", "错误"),
    ]

    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default="action", verbose_name="事件类型")
    event_name = models.CharField(max_length=100, db_index=True, verbose_name="事件名称")
    page_url = models.CharField(max_length=500, blank=True, default="", verbose_name="页面地址")
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="analytics_events", verbose_name="用户",
    )
    session_key = models.CharField(max_length=100, blank=True, default="", db_index=True, verbose_name="会话")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    user_agent = models.CharField(max_length=500, blank=True, default="", verbose_name="UA")
    referrer = models.CharField(max_length=500, blank=True, default="", verbose_name="来源")
    payload = models.JSONField(default=dict, blank=True, verbose_name="自定义参数")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="时间")

    class Meta:
        db_table = "analytics_event"
        ordering = ["-created_at"]
        verbose_name = "埋点事件"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.event_name} @ {self.page_url} ({self.created_at:%Y-%m-%d %H:%M:%S})"
