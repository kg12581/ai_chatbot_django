"""抖音热点数据展示视图"""

import json
import logging

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from api.models import DouyinHotSearch, SchedulerConfig
from api.crawler import fetch_and_save, _douyin_search_url
from api.weibo_crawler import _weibo_search_url
from tools.scheduler import scheduler_manager, validate_cron

logger = logging.getLogger(__name__)

# 抖音热搜任务默认配置
DOUYIN_TASK_ID = "douyin_hot_crawler"
DOUYIN_TASK_NAME = "抖音热搜爬虫"
DOUYIN_FUNC_PATH = "api.views._scheduled_crawl"
DOUYIN_DEFAULT_CRON = "0 * * * *"  # 每小时整点

# 微博热搜任务默认配置
WEIBO_TASK_ID = "weibo_hot_crawler"
WEIBO_TASK_NAME = "微博热搜爬虫"
WEIBO_FUNC_PATH = "api.views._scheduled_weibo_crawl"
WEIBO_DEFAULT_CRON = "0 * * * *"  # 每小时整点


# 标签样式映射
LABEL_STYLE = {
    "hot": {"text": "热", "class": "bg-red-500/20 text-red-400 border-red-500/30"},
    "new": {"text": "新", "class": "bg-blue-500/20 text-blue-400 border-blue-500/30"},
    "boil": {"text": "沸", "class": "bg-orange-500/20 text-orange-400 border-orange-500/30"},
    "normal": {"text": "", "class": ""},
}


def _scheduled_crawl():
    """定时任务执行的爬虫函数（记录执行结果到数据库）"""
    try:
        result = fetch_and_save()
        config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
        if config:
            config.last_run_at = timezone.now()
            config.last_run_result = f"成功: {result['total']} 条"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.info(f"定时爬取完成: {result['total']} 条")
    except Exception as e:
        config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
        if config:
            config.last_run_at = timezone.now()
            config.last_run_result = f"失败: {str(e)[:200]}"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.error(f"定时爬取失败: {e}")


def _scheduled_weibo_crawl():
    """定时任务执行的微博爬虫函数（记录执行结果到数据库）"""
    from api.weibo_crawler import fetch_and_save as weibo_fetch_and_save

    try:
        result = weibo_fetch_and_save()
        config = SchedulerConfig.objects.filter(task_id=WEIBO_TASK_ID).first()
        if config:
            config.last_run_at = timezone.now()
            config.last_run_result = f"成功: {result['total']} 条"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.info(f"微博定时爬取完成: {result['total']} 条")
    except Exception as e:
        config = SchedulerConfig.objects.filter(task_id=WEIBO_TASK_ID).first()
        if config:
            config.last_run_at = timezone.now()
            config.last_run_result = f"失败: {str(e)[:200]}"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.error(f"微博定时爬取失败: {e}")


@login_required
def douyin_hot(request):
    """抖音热搜榜页面"""
    # 获取最新一批数据
    latest = DouyinHotSearch.objects.order_by("-crawl_batch", "rank").first()
    if latest:
        items = DouyinHotSearch.objects.filter(
            crawl_batch=latest.crawl_batch
        ).order_by("rank")
    else:
        items = []

    # 爬取历史批次
    batches = (
        DouyinHotSearch.objects.values_list("crawl_batch", flat=True)
        .distinct()
        .order_by("-crawl_batch")[:10]
    )

    # 为每条数据附加标签样式
    item_list = []
    for item in items:
        style = LABEL_STYLE.get(item.label, LABEL_STYLE["normal"])
        item_list.append({
            "rank": item.rank,
            "title": item.title,
            "hot_value": item.hot_value,
            "label": item.label,
            "label_text": style["text"],
            "label_class": style["class"],
            "url": item.url or _douyin_search_url(item.title),
            "cover_url": item.cover_url,
        })

    context = {
        "items": item_list,
        "batches": list(batches),
        # 数据库存储本地时间（USE_TZ=False）
        "latest_batch": latest.crawl_batch.strftime("%Y-%m-%d %H:%M:%S") if latest else None,
        "total_count": DouyinHotSearch.objects.count(),
        "scheduler": _get_scheduler_context(
            DOUYIN_TASK_ID, DOUYIN_TASK_NAME, DOUYIN_FUNC_PATH, DOUYIN_DEFAULT_CRON
        ),
    }
    return render(request, "api/douyin_hot.html", context)


def _get_scheduler_context(task_id: str, task_name: str, func_path: str, default_cron: str):
    """获取调度器配置上下文"""
    config = SchedulerConfig.objects.filter(task_id=task_id).first()
    if not config:
        config = SchedulerConfig.objects.create(
            task_id=task_id,
            task_name=task_name,
            func_path=func_path,
            cron_expr=default_cron,
            enabled=False,
        )

    status = scheduler_manager.get_status()
    jobs = {j["id"]: j for j in status["jobs"]}
    job_info = jobs.get(task_id, {})

    from tools.scheduler import _cron_to_human
    return {
        "cron_expr": config.cron_expr,
        "enabled": config.enabled,
        "running": status["running"],
        "next_run": job_info.get("next_run"),
        "last_run_at": config.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if config.last_run_at else None,
        "last_run_result": config.last_run_result,
        "run_count": config.run_count,
        "human_readable": _cron_to_human(config.cron_expr),
    }


@login_required
@csrf_exempt
def douyin_crawl(request):
    """触发爬取抖音热搜 API"""
    if request.method == "POST":
        result = fetch_and_save()
        return JsonResponse({
            "success": True,
            "total": result["total"],
            "batch_time": result["batch_time"],
            "items": result["items"],
        })
    return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)


# ===== 微博热搜视图 =====


@login_required
def weibo_hot(request):
    """微博热搜榜页面"""
    from api.models import WeiboHotSearch

    # 获取最新一批数据
    latest = WeiboHotSearch.objects.order_by("-crawl_batch", "rank").first()
    if latest:
        items = WeiboHotSearch.objects.filter(
            crawl_batch=latest.crawl_batch
        ).order_by("rank")
    else:
        items = []

    # 爬取历史批次
    batches = (
        WeiboHotSearch.objects.values_list("crawl_batch", flat=True)
        .distinct()
        .order_by("-crawl_batch")[:10]
    )

    # 为每条数据附加标签样式
    item_list = []
    for item in items:
        style = LABEL_STYLE.get(item.label, LABEL_STYLE["normal"])
        item_list.append({
            "rank": item.rank,
            "title": item.title,
            "hot_value": item.hot_value,
            "label": item.label,
            "label_text": style["text"],
            "label_class": style["class"],
            "url": item.url or _weibo_search_url(item.title),
            "cover_url": item.cover_url,
        })

    context = {
        "items": item_list,
        "batches": list(batches),
        "latest_batch": latest.crawl_batch.strftime("%Y-%m-%d %H:%M:%S") if latest else None,
        "total_count": WeiboHotSearch.objects.count(),
        "scheduler": _get_scheduler_context(
            WEIBO_TASK_ID, WEIBO_TASK_NAME, WEIBO_FUNC_PATH, WEIBO_DEFAULT_CRON
        ),
    }
    return render(request, "api/weibo_hot.html", context)


@login_required
@csrf_exempt
def weibo_crawl(request):
    """触发爬取微博热搜 API"""
    from api.weibo_crawler import fetch_and_save as weibo_fetch_and_save

    if request.method == "POST":
        result = weibo_fetch_and_save()
        return JsonResponse({
            "success": True,
            "total": result["total"],
            "batch_time": result["batch_time"],
            "items": result["items"],
        })
    return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)


# ===== 定时调度管理 API =====


@login_required
@csrf_exempt
def scheduler_status(request):
    """获取调度器状态"""
    if request.method == "GET":
        data = _get_scheduler_context(
            DOUYIN_TASK_ID, DOUYIN_TASK_NAME, DOUYIN_FUNC_PATH, DOUYIN_DEFAULT_CRON
        )
        return JsonResponse({"success": True, "data": data})
    return JsonResponse({"success": False, "error": "仅支持 GET 请求"}, status=405)


@login_required
@csrf_exempt
def scheduler_start(request):
    """启动定时任务"""
    return _scheduler_start(
        request, DOUYIN_TASK_ID, DOUYIN_TASK_NAME, DOUYIN_FUNC_PATH, DOUYIN_DEFAULT_CRON
    )


@login_required
@csrf_exempt
def scheduler_stop(request):
    """停止定时任务"""
    return _scheduler_stop(request, DOUYIN_TASK_ID)


@login_required
@csrf_exempt
def weibo_scheduler_status(request):
    """获取微博调度器状态"""
    if request.method == "GET":
        data = _get_scheduler_context(
            WEIBO_TASK_ID, WEIBO_TASK_NAME, WEIBO_FUNC_PATH, WEIBO_DEFAULT_CRON
        )
        return JsonResponse({"success": True, "data": data})
    return JsonResponse({"success": False, "error": "仅支持 GET 请求"}, status=405)


@login_required
@csrf_exempt
def weibo_scheduler_start(request):
    """启动微博定时任务"""
    return _scheduler_start(
        request, WEIBO_TASK_ID, WEIBO_TASK_NAME, WEIBO_FUNC_PATH, WEIBO_DEFAULT_CRON
    )


@login_required
@csrf_exempt
def weibo_scheduler_stop(request):
    """停止微博定时任务"""
    return _scheduler_stop(request, WEIBO_TASK_ID)


def _scheduler_start(request, task_id: str, task_name: str, func_path: str, default_cron: str):
    """启动定时任务（通用实现）"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    cron_expr = data.get("cron_expr", "").strip()

    config = SchedulerConfig.objects.filter(task_id=task_id).first()
    if not config:
        config = SchedulerConfig.objects.create(
            task_id=task_id,
            task_name=task_name,
            func_path=func_path,
            cron_expr=default_cron,
        )

    # 如果传了新的 cron 表达式，先验证
    if cron_expr:
        validation = validate_cron(cron_expr)
        if not validation["valid"]:
            return JsonResponse({"success": False, "error": validation["message"]})
        config.cron_expr = cron_expr

    # 启动调度器并添加任务
    scheduler_manager.start()
    scheduler_manager.add_job(
        job_id=task_id,
        func=func_path,
        cron_expr=config.cron_expr,
    )

    config.enabled = True
    config.save()

    status = scheduler_manager.get_status()
    jobs = {j["id"]: j for j in status["jobs"]}
    job_info = jobs.get(task_id, {})

    return JsonResponse({
        "success": True,
        "message": f"定时任务已启动 (cron: {config.cron_expr})",
        "next_run": job_info.get("next_run"),
    })


def _scheduler_stop(request, task_id: str):
    """停止定时任务（通用实现）"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)

    scheduler_manager.remove_job(task_id)

    config = SchedulerConfig.objects.filter(task_id=task_id).first()
    if config:
        config.enabled = False
        config.save()

    return JsonResponse({"success": True, "message": "定时任务已停止"})
