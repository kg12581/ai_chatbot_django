"""抖音/微博热搜爬虫测试"""

from unittest import mock

import pytest
import requests

from api import crawler, weibo_crawler
from api.models import DouyinHotSearch, WeiboHotSearch


def _mock_get(payload=None, exc=None):
    resp = mock.Mock()
    resp.json.return_value = payload if payload is not None else {}
    resp.raise_for_status.return_value = None
    if exc:
        resp.raise_for_status.side_effect = exc
    return resp


# ===== 抖音爬虫 =====


class TestDouyinCrawler:
    def test_new_format_top_level_word_list(self):
        payload = {
            "status_code": 0,
            "word_list": [
                {"word": "话题一", "hot_value": 1000, "label": 1},
                {"word": "话题二", "hot_value": 2000, "label": 0},
                {"word": "话题三", "hot_value": 3000, "label": 2},
            ],
        }
        with mock.patch.object(crawler.requests, "get", return_value=_mock_get(payload)):
            items = crawler.crawl_douyin_hot()
        assert len(items) == 3
        assert items[0]["rank"] == 1
        assert items[0]["title"] == "话题一"
        assert items[0]["label"] == "hot"
        assert "douyin.com/search" in items[0]["url"]
        assert items[1]["label"] == "normal"
        assert items[2]["label"] == "new"

    def test_old_format_billboard_data(self):
        payload = {"billboard_data": {"word_list": [{"word": "旧格式", "hot_value": 99, "label": 3}]}}
        with mock.patch.object(crawler.requests, "get", return_value=_mock_get(payload)):
            items = crawler.crawl_douyin_hot()
        assert len(items) == 1
        assert items[0]["title"] == "旧格式"
        assert items[0]["label"] == "boil"
        assert "douyin.com/search" in items[0]["url"]

    def test_empty_list_falls_back_to_mock(self):
        with mock.patch.object(crawler.requests, "get", return_value=_mock_get({"word_list": []})):
            items = crawler.crawl_douyin_hot()
        assert len(items) == 20  # 模拟数据兜底
        assert all("douyin.com/search" in i["url"] for i in items)

    def test_request_error_falls_back_to_mock(self):
        with mock.patch.object(
            crawler.requests, "get",
            side_effect=requests.RequestException("network down"),
        ):
            items = crawler.crawl_douyin_hot()
        assert len(items) == 20

    @pytest.mark.django_db
    def test_save_to_db(self):
        items = [{"rank": 1, "title": "话题", "hot_value": 1, "label": "hot", "url": "https://www.douyin.com/search/话题", "cover_url": ""}]
        assert crawler.save_to_db(items) == 1
        assert DouyinHotSearch.objects.count() == 1
        assert DouyinHotSearch.objects.first().rank == 1
        assert "douyin.com" in DouyinHotSearch.objects.first().url


# ===== 微博爬虫 =====


class TestWeiboCrawler:
    def test_parse_and_label_mapping(self):
        payload = {
            "data": {
                "realtime": [
                    {"word": "爆款话题", "num": 5000, "label_name": "爆", "rank": 0},
                    {"word": "热话题", "num": 4000, "label_name": "热"},
                    {"word": "新话题", "num": 3000, "label_name": "新"},
                ]
            }
        }
        with mock.patch.object(weibo_crawler.requests, "get", return_value=_mock_get(payload)):
            items = weibo_crawler.crawl_weibo_hot()
        # 排名统一重排为 1..N
        assert [i["rank"] for i in items] == [1, 2, 3]
        assert items[0]["label"] == "boil"  # 爆 → boil
        assert items[1]["label"] == "hot"
        assert items[2]["label"] == "new"

    def test_url_fallback(self):
        payload = {"data": {"realtime": [{"word": "没有链接的话题", "num": 1, "label_name": ""}]}}
        with mock.patch.object(weibo_crawler.requests, "get", return_value=_mock_get(payload)):
            items = weibo_crawler.crawl_weibo_hot()
        assert "s.weibo.com" in items[0]["url"]

    def test_non_http_url_falls_back(self):
        # 微博接口 url 字段可能是 "#话题#" 纯文本，不能当链接用
        payload = {"data": {"realtime": [{"word": "文本话题", "num": 1, "label_name": "", "url": "#文本话题#"}]}}
        with mock.patch.object(weibo_crawler.requests, "get", return_value=_mock_get(payload)):
            items = weibo_crawler.crawl_weibo_hot()
        assert items[0]["url"].startswith("https://s.weibo.com/weibo?q=")

    def test_empty_falls_back_to_mock(self):
        with mock.patch.object(weibo_crawler.requests, "get", return_value=_mock_get({"data": {"realtime": []}})):
            items = weibo_crawler.crawl_weibo_hot()
        assert len(items) == 20

    @pytest.mark.django_db
    def test_save_to_db(self):
        items = [{"rank": 1, "title": "话题", "hot_value": 1, "label": "hot", "url": "https://s.weibo.com", "cover_url": ""}]
        assert weibo_crawler.save_to_db(items) == 1
        assert WeiboHotSearch.objects.count() == 1
        assert WeiboHotSearch.objects.first().url == "https://s.weibo.com"
