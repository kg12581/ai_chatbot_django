"""硬编码密钥扫描 Web 视图"""

import json
import logging
import threading
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from scanner.models import ScanRun, SecretFinding
from tools.secret_scanner import ScanTimeoutError, scan_target

logger = logging.getLogger(__name__)

# 保留最近多少次扫描记录，更早的自动清理
KEEP_RECENT_RUNS = 20
# 扫描资源上限：防止超大仓库拖垮服务
SCAN_MAX_SECONDS = 120
SCAN_MAX_FILES = 20000
CLONE_TIMEOUT_SECONDS = 120
STALE_RUN_MINUTES = 10

# 同一时间只允许一个扫描任务
_scan_lock = threading.Lock()


@login_required
def scanner_home(request):
    """硬编码扫描页面"""
    latest = ScanRun.objects.first()
    findings = list(latest.findings.all()) if latest else []
    stats = {
        "open": sum(1 for f in findings if f.status == "open"),
        "false_positive": sum(1 for f in findings if f.status == "false_positive"),
        "fixed": sum(1 for f in findings if f.status == "fixed"),
    }
    context = {
        "latest": latest,
        "findings": findings,
        "stats": stats,
        "recent_runs": ScanRun.objects.all()[:10],
    }
    return render(request, "scanner/scan.html", context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def scanner_run(request):
    """启动一次硬编码扫描（后台异步执行，立即返回）"""
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "请求体不是合法 JSON"}, status=400)

    target = (data.get("target") or "").strip()
    # 扫描其他代码仓属于敏感操作，仅限管理员
    if target and not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"success": False, "error": "仅管理员可扫描指定代码仓"}, status=403)

    if target.startswith(("http://", "https://")):
        source_type, display_target = "url", target
    elif target:
        source_type, display_target = "path", target
    else:
        source_type, display_target = "project", "当前项目"

    # 清理陈旧的"扫描中"记录（如服务器重启导致残留）
    from django.utils import timezone
    from datetime import timedelta
    ScanRun.objects.filter(
        status="running",
        created_at__lt=timezone.now() - timedelta(minutes=STALE_RUN_MINUTES),
    ).update(status="failed", error_message="扫描进程中断，已标记为失败")

    # 并发保护：同一时间只允许一个扫描
    if ScanRun.objects.filter(status="running").exists():
        return JsonResponse({"success": False, "error": "已有扫描正在进行中，请稍后再试"}, status=409)

    run = ScanRun.objects.create(
        status="running",
        source_type=source_type,
        target_path=display_target,
    )

    # 后台线程执行，避免大仓库阻塞请求
    thread = threading.Thread(
        target=_scan_worker,
        args=(run.pk, target),
        daemon=True,
        name=f"secret-scan-{run.pk}",
    )
    thread.start()

    return JsonResponse({
        "success": True,
        "async": True,
        "run_id": run.pk,
        "message": "扫描已开始，请稍候查看结果",
    })


def _scan_worker(run_id: int, target: str):
    """后台执行扫描并更新 ScanRun（线程内使用独立 DB 连接）。"""
    from django.db import connections

    run = ScanRun.objects.get(pk=run_id)
    start = time.monotonic()
    try:
        result = scan_target(
            target,
            str(settings.BASE_DIR),
            max_seconds=SCAN_MAX_SECONDS,
            max_files=SCAN_MAX_FILES,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        findings = [
            SecretFinding(
                scan_run=run,
                rule_id=f["rule_id"],
                rule_name=f["rule_name"],
                severity=f["severity"],
                file_path=f["file_path"],
                line_number=f["line_number"],
                line_text=f["line_text"],
                secret_preview=f["secret_preview"],
                entropy=f["entropy"],
            )
            for f in result["findings"]
        ]
        SecretFinding.objects.bulk_create(findings)

        run.status = "finished"
        run.files_scanned = result["files_scanned"]
        run.findings_count = len(findings)
        run.duration_ms = duration_ms
        run.error_message = ""
        run.save(update_fields=["status", "files_scanned", "findings_count", "duration_ms", "error_message"])
        logger.info(f"后台扫描完成 run#{run_id}: {result['files_scanned']} 文件, {len(findings)} 处")
    except ScanTimeoutError as e:
        run.status = "failed"
        run.error_message = str(e)
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save(update_fields=["status", "duration_ms", "error_message"])
        logger.warning(f"扫描超时 run#{run_id}: {e}")
    except ValueError as e:
        run.status = "failed"
        run.error_message = str(e)
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save(update_fields=["status", "duration_ms", "error_message"])
        logger.warning(f"扫描目标无效 run#{run_id}: {e}")
    except Exception as e:
        logger.exception(f"后台扫描失败 run#{run_id}")
        run.status = "failed"
        run.error_message = f"扫描失败: {e}"
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save(update_fields=["status", "duration_ms", "error_message"])
    finally:
        # 清理过旧记录，避免无限增长
        try:
            old_ids = list(ScanRun.objects.order_by("-id")[KEEP_RECENT_RUNS:].values_list("id", flat=True))
            if old_ids:
                SecretFinding.objects.filter(scan_run_id__in=old_ids).delete()
                ScanRun.objects.filter(id__in=old_ids).delete()
        finally:
            connections.close_all()


@login_required
def scanner_status(request, run_id):
    """查询扫描进度（前端轮询用）"""
    run = ScanRun.objects.filter(pk=run_id).first()
    if not run:
        return JsonResponse({"success": False, "error": "扫描记录不存在"}, status=404)
    return JsonResponse({
        "success": True,
        "run": {
            "id": run.pk,
            "status": run.status,
            "source_type": run.source_type,
            "target_path": run.target_path,
            "files_scanned": run.files_scanned,
            "findings_count": run.findings_count,
            "duration_ms": run.duration_ms,
            "error_message": run.error_message,
            "created_at": run.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def scanner_update_status(request, pk):
    """更新单条发现的处理状态（待处理/误报/已修复）"""
    finding = get_object_or_404(SecretFinding, pk=pk)
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "请求体不是合法 JSON"}, status=400)

    status = data.get("status")
    valid = {k for k, _ in SecretFinding.STATUS_CHOICES}
    if status not in valid:
        return JsonResponse({"success": False, "error": f"无效状态，可选: {', '.join(sorted(valid))}"}, status=400)

    finding.status = status
    finding.save(update_fields=["status"])
    return JsonResponse({"success": True, "status": status})
