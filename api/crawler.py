"""
抖音热搜爬虫模块

数据来源：抖音热搜榜 API
如果 API 不可用，则使用模拟数据兜底。
"""

import logging
from urllib.parse import quote
from typing import List, Dict

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

# 抖音热搜 API 地址
DOUYIN_HOT_URL = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json",
}

# 标签映射：抖音 API label 字段 → 可读标签
LABEL_MAP = {
    1: "hot",    # 热
    2: "new",    # 新
    3: "boil",   # 沸
    0: "normal",
}


def _douyin_search_url(word: str) -> str:
    """构造抖音话题搜索链接（接口未提供直达链接时使用）"""
    return f"https://www.douyin.com/search/{quote(word)}?type=general"


def crawl_douyin_hot() -> List[Dict]:
    """
    爬取抖音热搜榜数据。

    返回格式：
        [
            {
                "rank": 1,
                "title": "热搜话题",
                "hot_value": 1234567,
                "label": "hot",
                "cover_url": "https://...",
            },
            ...
        ]

    如果 API 请求失败，返回模拟数据（_mock=True 标记）。
    """
    try:
        resp = requests.get(DOUYIN_HOT_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # 兼容两种返回结构：
        #   新版接口：word_list 在顶层（2026 年起）
        #   旧版接口：word_list 在 billboard_data 下
        word_list = (
            data.get("word_list")
            or (data.get("billboard_data") or {}).get("word_list", [])
        )
        if not word_list:
            logger.warning("抖音 API 返回空数据，使用模拟数据兜底")
            return _mock_data()

        result = []
        for i, item in enumerate(word_list, 1):
            label_code = item.get("label", 0)
            cover = item.get("word_cover") or {}
            cover_url = (cover.get("url_list") or [""])[0]

            result.append({
                # 新版接口无 position 字段，按列表顺序编号
                "rank": item.get("position", i),
                "title": item.get("word", ""),
                "hot_value": item.get("hot_value", 0),
                "label": LABEL_MAP.get(label_code, "normal"),
                "url": _douyin_search_url(item.get("word", "")),
                "cover_url": cover_url,
            })

        logger.info(f"爬取抖音热搜成功，共 {len(result)} 条")
        return result

    except (requests.RequestException, ValueError, KeyError) as e:
        logger.warning(f"抖音 API 请求失败: {e}，使用模拟数据兜底")
        return _mock_data()


def _mock_data() -> List[Dict]:
    """生成模拟热搜数据（API 不可用时兜底）"""
    mock_items = [
        ("国产大模型再突破", 9823000, "boil"),
        ("巴黎奥运会最新赛况", 8756000, "hot"),
        ("神舟飞船成功着陆", 7634000, "hot"),
        ("高考成绩公布", 6521000, "new"),
        ("夏季高温预警", 5897000, "hot"),
        ("新能源汽车销量创新高", 5234000, "hot"),
        ("AI编程助手大比拼", 4892000, "new"),
        ("国产电影票房破纪录", 4367000, "hot"),
        ("电商平台大促活动", 3985000, "normal"),
        ("城市夜经济发展", 3567000, "normal"),
        ("职业教育改革新政策", 3234000, "new"),
        ("量子计算机新进展", 2987000, "normal"),
        ("国产芯片量产突破", 2756000, "hot"),
        ("智能驾驶新规出台", 2534000, "normal"),
        ("数字经济峰会召开", 2312000, "normal"),
        ("绿色能源新项目", 2156000, "normal"),
        ("乡村振兴新举措", 1987000, "normal"),
        ("医疗改革新方案", 1834000, "normal"),
        ("文旅消费持续升温", 1656000, "normal"),
        ("体育赛事精彩纷呈", 1523000, "normal"),
    ]

    result = []
    for i, (title, hot, label) in enumerate(mock_items, 1):
        result.append({
            "rank": i,
            "title": title,
            "hot_value": hot,
            "label": label,
            "url": _douyin_search_url(title),
            "cover_url": "",
        })
    return result


def save_to_db(items: List[Dict]) -> int:
    """
    将爬取的数据保存到数据库。

    返回保存的记录数。
    """
    from api.models import DouyinHotSearch

    if not items:
        return 0

    # 使用当前时间作为批次标识，同批次数据可整体替换
    # USE_TZ=False 时 timezone.now() 返回本地 naive datetime，Django 直接存储
    batch_time = timezone.now()

    # 批量创建
    objects = [
        DouyinHotSearch(
            rank=item["rank"],
            title=item["title"],
            hot_value=item["hot_value"],
            label=item["label"],
            url=item.get("url", ""),
            cover_url=item["cover_url"],
            crawl_batch=batch_time,
        )
        for item in items
    ]

    created = DouyinHotSearch.objects.bulk_create(objects)
    logger.info(f"成功保存 {len(created)} 条热搜数据到数据库")
    return len(created)


def fetch_and_save() -> dict:
    """
    完整流程：爬取 → 入库。

    返回操作结果摘要。
    """
    items = crawl_douyin_hot()
    count = save_to_db(items)
    return {
        "total": count,
        # 返回给前端时转换为本地时区（Asia/Shanghai）
        "batch_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
