"""埋点上报与统计视图"""

import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from common.analytics_models import AnalyticsEvent

logger = logging.getLogger(__name__)

# 上报参数限制
MAX_PAYLOAD_KEYS = 20
MAX_PAYLOAD_VALUE_LEN = 200

VALID_EVENT_TYPES = {k for k, _ in AnalyticsEvent.EVENT_TYPES}


def _clean_payload(raw) -> dict:
    """清洗自定义参数：只保留字符串/数字/布尔，限制数量与长度。"""
    if not isinstance(raw, dict):
        return {}
    cleaned = {}
    for k, v in raw.items():
        if len(cleaned) >= MAX_PAYLOAD_KEYS:
            break
        if isinstance(v, str):
            v = v[:MAX_PAYLOAD_VALUE_LEN]
        elif not isinstance(v, (int, float, bool)):
            continue
        cleaned[str(k)[:50]] = v
    return cleaned


@csrf_exempt
@require_http_methods(["POST"])
def track_event(request):
    """埋点上报接口（支持登录与匿名）"""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "请求体不是合法 JSON"}, status=400)

    event_type = str(data.get("event_type") or "action").strip()
    event_name = str(data.get("event_name") or "").strip()[:100]
    if not event_name:
        return JsonResponse({"success": False, "error": "event_name 不能为空"}, status=400)
    if event_type not in VALID_EVENT_TYPES:
        event_type = "action"

    AnalyticsEvent.objects.create(
        event_type=event_type,
        event_name=event_name,
        page_url=str(data.get("page_url") or "")[:500],
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
        ip=_client_ip(request),
        user_agent=str(request.META.get("HTTP_USER_AGENT") or "")[:500],
        referrer=str(request.META.get("HTTP_REFERER") or "")[:500],
        payload=_clean_payload(data.get("payload")),
    )
    return JsonResponse({"success": True})


def _client_ip(request):
    """获取客户端 IP（优先 X-Forwarded-For）"""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


@login_required
def analytics_dashboard(request):
    """埋点统计页"""
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    total = AnalyticsEvent.objects.count()
    today = AnalyticsEvent.objects.filter(created_at__gte=today_start).count()
    pv = AnalyticsEvent.objects.filter(event_type="pageview").count()
    uv = (
        AnalyticsEvent.objects.filter(event_type="pageview")
        .values("session_key", "user_id")
        .distinct()
        .count()
    )

    event_ranking = (
        AnalyticsEvent.objects.filter(created_at__gte=week_start)
        .values("event_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:15]
    )
    top_pages = (
        AnalyticsEvent.objects.filter(event_type="pageview")
        .values("page_url")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    recent = AnalyticsEvent.objects.all()[:50]

    context = {
        "total": total,
        "today": today,
        "pv": pv,
        "uv": uv,
        "event_ranking": event_ranking,
        "top_pages": top_pages,
        "recent": recent,
    }
    return render(request, "analytics/dashboard.html", context)
