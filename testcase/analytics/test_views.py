"""埋点上报与统计视图测试"""

import json

import pytest
from django.urls import reverse

from common.analytics_models import AnalyticsEvent


@pytest.mark.django_db
def test_track_anonymous_event(client):
    resp = client.post(
        reverse("track_event"),
        data=json.dumps({"event_type": "click", "event_name": "douyin_crawl", "page_url": "/api/douyin/hot/", "payload": {"source": "page"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    event = AnalyticsEvent.objects.first()
    assert event.event_name == "douyin_crawl"
    assert event.event_type == "click"
    assert event.user is None
    assert event.payload == {"source": "page"}


@pytest.mark.django_db
def test_track_requires_event_name(client):
    resp = client.post(reverse("track_event"), data="{}", content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_track_invalid_json(client):
    resp = client.post(reverse("track_event"), data="not-json", content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_track_logged_user(client, django_user_model):
    user = django_user_model.objects.create_user("tracker", password="pw")
    client.force_login(user)
    client.post(
        reverse("track_event"),
        data=json.dumps({"event_name": "pageview", "event_type": "pageview", "page_url": "/"}),
        content_type="application/json",
    )
    assert AnalyticsEvent.objects.first().user == user


@pytest.mark.django_db
def test_track_payload_cleaned(client):
    big = "x" * 500
    payload = {"long": big, "ok": 1, "bad": [1, 2], "other": True}
    for i in range(30):
        payload[f"k{i}"] = i
    client.post(
        reverse("track_event"),
        data=json.dumps({"event_name": "action", "payload": payload}),
        content_type="application/json",
    )
    saved = AnalyticsEvent.objects.first().payload
    assert saved["long"] == "x" * 200          # 超长截断
    assert saved["ok"] == 1
    assert "bad" not in saved                  # 非标量丢弃
    assert len(saved) <= 20                    # 数量上限


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    assert client.get(reverse("analytics_dashboard")).status_code == 302


@pytest.mark.django_db
def test_dashboard_page(client, django_user_model):
    user = django_user_model.objects.create_user("u", password="pw")
    client.force_login(user)
    AnalyticsEvent.objects.create(event_name="pageview", event_type="pageview", page_url="/")
    resp = client.get(reverse("analytics_dashboard"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "数据统计" in body
    assert "页面访问" in body
