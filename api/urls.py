from django.urls import path

from api.views import (
    douyin_hot,
    douyin_crawl,
    weibo_hot,
    weibo_crawl,
    scheduler_status,
    scheduler_start,
    scheduler_stop,
    weibo_scheduler_status,
    weibo_scheduler_start,
    weibo_scheduler_stop,
)

urlpatterns = [
    path("douyin/hot/", douyin_hot, name="douyin_hot"),
    path("douyin/crawl/", douyin_crawl, name="douyin_crawl"),
    path("weibo/hot/", weibo_hot, name="weibo_hot"),
    path("weibo/crawl/", weibo_crawl, name="weibo_crawl"),
    path("scheduler/status/", scheduler_status, name="scheduler_status"),
    path("scheduler/start/", scheduler_start, name="scheduler_start"),
    path("scheduler/stop/", scheduler_stop, name="scheduler_stop"),
    path("weibo/scheduler/status/", weibo_scheduler_status, name="weibo_scheduler_status"),
    path("weibo/scheduler/start/", weibo_scheduler_start, name="weibo_scheduler_start"),
    path("weibo/scheduler/stop/", weibo_scheduler_stop, name="weibo_scheduler_stop"),
]
