"""抖音热点数据展示视图"""

import json
import logging
from datetime import datetime, timezone

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from api.models import DouyinHotSearch, SchedulerConfig
from api.crawler import fetch_and_save
from tools.scheduler import scheduler_manager, validate_cron

logger = logging.getLogger(__name__)

# 抖音热搜任务默认配置
DOUYIN_TASK_ID = "douyin_hot_crawler"
DOUYIN_TASK_NAME = "抖音热搜爬虫"
DOUYIN_FUNC_PATH = "api.views._scheduled_crawl"
DOUYIN_DEFAULT_CRON = "0 * * * *"  # 每小时整点


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
            config.last_run_at = datetime.now(timezone.utc)
            config.last_run_result = f"成功: {result['total']} 条"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.info(f"定时爬取完成: {result['total']} 条")
    except Exception as e:
        config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
        if config:
            config.last_run_at = datetime.now(timezone.utc)
            config.last_run_result = f"失败: {str(e)[:200]}"
            config.run_count += 1
            config.save(update_fields=["last_run_at", "last_run_result", "run_count"])
        logger.error(f"定时爬取失败: {e}")


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
            "cover_url": item.cover_url,
        })

    context = {
        "items": item_list,
        "batches": list(batches),
        "latest_batch": latest.crawl_batch.strftime("%Y-%m-%d %H:%M:%S") if latest else None,
        "total_count": DouyinHotSearch.objects.count(),
        "scheduler": _get_scheduler_context(),
    }
    return render(request, "api/douyin_hot.html", context)


def _get_scheduler_context():
    """获取调度器配置上下文"""
    config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
    if not config:
        config = SchedulerConfig.objects.create(
            task_id=DOUYIN_TASK_ID,
            task_name=DOUYIN_TASK_NAME,
            func_path=DOUYIN_FUNC_PATH,
            cron_expr=DOUYIN_DEFAULT_CRON,
            enabled=False,
        )

    status = scheduler_manager.get_status()
    jobs = {j["id"]: j for j in status["jobs"]}
    job_info = jobs.get(DOUYIN_TASK_ID, {})

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


# ===== 定时调度管理 API =====


@csrf_exempt
def scheduler_status(request):
    """获取调度器状态"""
    if request.method == "GET":
        return JsonResponse({"success": True, "data": _get_scheduler_context()})
    return JsonResponse({"success": False, "error": "仅支持 GET 请求"}, status=405)


@csrf_exempt
def scheduler_start(request):
    """启动定时任务"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    cron_expr = data.get("cron_expr", "").strip()

    config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
    if not config:
        config = SchedulerConfig.objects.create(
            task_id=DOUYIN_TASK_ID,
            task_name=DOUYIN_TASK_NAME,
            func_path=DOUYIN_FUNC_PATH,
            cron_expr=DOUYIN_DEFAULT_CRON,
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
        job_id=DOUYIN_TASK_ID,
        func=DOUYIN_FUNC_PATH,
        cron_expr=config.cron_expr,
    )

    config.enabled = True
    config.save()

    status = scheduler_manager.get_status()
    jobs = {j["id"]: j for j in status["jobs"]}
    job_info = jobs.get(DOUYIN_TASK_ID, {})

    return JsonResponse({
        "success": True,
        "message": f"定时任务已启动 (cron: {config.cron_expr})",
        "next_run": job_info.get("next_run"),
    })


@csrf_exempt
def scheduler_stop(request):
    """停止定时任务"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "仅支持 POST 请求"}, status=405)

    scheduler_manager.remove_job(DOUYIN_TASK_ID)

    config = SchedulerConfig.objects.filter(task_id=DOUYIN_TASK_ID).first()
    if config:
        config.enabled = False
        config.save()

    return JsonResponse({"success": True, "message": "定时任务已停止"})
