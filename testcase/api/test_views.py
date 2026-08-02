"""热搜/调度视图测试"""

from unittest import mock

import pytest
from django.urls import reverse


@pytest.fixture
def logged_client(db, client, django_user_model):
    user = django_user_model.objects.create_user("tester", password="pw")
    client.force_login(user)
    return client


# ===== 页面 =====


@pytest.mark.django_db
def test_douyin_hot_requires_login(client):
    assert client.get(reverse("douyin_hot")).status_code == 302


@pytest.mark.django_db
def test_weibo_hot_requires_login(client):
    assert client.get(reverse("weibo_hot")).status_code == 302


@pytest.mark.django_db
def test_douyin_hot_page(logged_client):
    resp = logged_client.get(reverse("douyin_hot"))
    assert resp.status_code == 200
    assert "抖音热搜榜" in resp.content.decode()


@pytest.mark.django_db
def test_weibo_hot_page(logged_client):
    resp = logged_client.get(reverse("weibo_hot"))
    assert resp.status_code == 200
    assert "微博热搜榜" in resp.content.decode()


# ===== 爬取接口 =====


@pytest.mark.django_db
def test_douyin_crawl(logged_client):
    canned = {"total": 3, "batch_time": "2026-01-01 00:00:00",
              "items": [{"rank": 1, "title": "t", "hot_value": 1, "label": "normal", "cover_url": ""}]}
    with mock.patch("api.views.fetch_and_save", return_value=canned):
        resp = logged_client.post(reverse("douyin_crawl"))
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


@pytest.mark.django_db
def test_weibo_crawl(logged_client):
    canned = {"total": 2, "batch_time": "2026-01-01 00:00:00",
              "items": [{"rank": 1, "title": "t", "hot_value": 1, "label": "hot", "url": "", "cover_url": ""}]}
    with mock.patch("api.weibo_crawler.fetch_and_save", return_value=canned):
        resp = logged_client.post(reverse("weibo_crawl"))
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.django_db
def test_crawl_get_method_rejected(logged_client):
    assert logged_client.get(reverse("douyin_crawl")).status_code == 405


# ===== 调度接口 =====


@pytest.mark.django_db
def test_scheduler_start_invalid_cron(logged_client):
    resp = logged_client.post(
        reverse("scheduler_start"), data='{"cron_expr": "not-a-cron"}',
        content_type="application/json",
    )
    body = resp.json()
    assert body["success"] is False
    assert "error" in body


@pytest.mark.django_db
def test_scheduler_stop(logged_client):
    resp = logged_client.post(reverse("scheduler_stop"))
    assert resp.json()["success"] is True


@pytest.mark.django_db
def test_weibo_scheduler_status(logged_client):
    resp = logged_client.get(reverse("weibo_scheduler_status"))
    assert resp.json()["success"] is True
