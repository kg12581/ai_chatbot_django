from django.urls import path

from api.views import (
    douyin_hot,
    douyin_crawl,
    scheduler_status,
    scheduler_start,
    scheduler_stop,
)

urlpatterns = [
    path("douyin/hot/", douyin_hot, name="douyin_hot"),
    path("douyin/crawl/", douyin_crawl, name="douyin_crawl"),
    path("scheduler/status/", scheduler_status, name="scheduler_status"),
    path("scheduler/start/", scheduler_start, name="scheduler_start"),
    path("scheduler/stop/", scheduler_stop, name="scheduler_stop"),
]
