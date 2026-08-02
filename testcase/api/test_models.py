"""数据模型测试"""

import pytest
from django.utils import timezone

from api.models import DouyinHotSearch, SchedulerConfig, WeiboHotSearch


@pytest.mark.django_db
def test_douyin_hot_search_model():
    item = DouyinHotSearch.objects.create(
        rank=1, title="抖音话题", hot_value=100, label="hot", crawl_batch=timezone.now(),
    )
    assert str(item) == "#1 抖音话题 (100)"
    assert item.label_display == "热"


@pytest.mark.django_db
def test_weibo_hot_search_model():
    item = WeiboHotSearch.objects.create(
        rank=2, title="微博话题", hot_value=200, label="new",
        url="https://s.weibo.com/weibo?q=话题", crawl_batch=timezone.now(),
    )
    assert str(item) == "#2 微博话题 (200)"
    assert item.label_display == "新"
    assert item.url.startswith("https://s.weibo.com")


@pytest.mark.django_db
def test_scheduler_config_model():
    config = SchedulerConfig.objects.create(
        task_id="test_task", task_name="测试任务", func_path="api.views._scheduled_crawl",
        cron_expr="0 * * * *", enabled=True,
    )
    assert "测试任务" in str(config)
    assert "ON" in str(config)
