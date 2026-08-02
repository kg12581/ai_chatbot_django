"""管理命令：导出埋点事件 CSV"""

import csv
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import AnalyticsEvent


class Command(BaseCommand):
    help = "导出埋点事件到 CSV（默认最近 7 天，输出到 analytics_export.csv）"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="导出最近 N 天，0 表示全部")
        parser.add_argument("--output", default="analytics_export.csv", help="输出文件路径")

    def handle(self, *args, **options):
        qs = AnalyticsEvent.objects.all()
        if options["days"] > 0:
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=options["days"]))

        path = Path(options["output"])
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["时间", "类型", "事件", "页面", "用户", "会话", "IP", "UA", "来源", "参数"])
            for e in qs.iterator():
                writer.writerow([
                    e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    e.get_event_type_display(),
                    e.event_name,
                    e.page_url,
                    e.user.username if e.user else "",
                    e.session_key,
                    e.ip or "",
                    e.user_agent,
                    e.referrer,
                    e.payload,
                ])
        self.stdout.write(self.style.SUCCESS(f"已导出 {qs.count()} 条埋点事件到 {path}"))
