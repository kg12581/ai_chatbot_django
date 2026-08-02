"""
定时调度工具

基于 APScheduler 的后台调度器，支持标准 cron 表达式。
支持动态添加/移除/暂停/恢复定时任务。

使用示例：
    from tools.scheduler import scheduler_manager

    # 添加任务（cron 表达式：分 时 日 月 周）
    scheduler_manager.add_job(
        job_id="douyin_hot",
        func="api.crawler.fetch_and_save",   # 模块路径字符串
        cron_expr="0 */1 * * *",             # 每小时执行
    )

    # 暂停 / 恢复
    scheduler_manager.pause_job("douyin_hot")
    scheduler_manager.resume_job("douyin_hot")

    # 移除
    scheduler_manager.remove_job("douyin_hot")

    # 查看状态
    scheduler_manager.get_status()
"""

import logging
import os
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerAlreadyRunningError, SchedulerNotRunningError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from django.db import connections

logger = logging.getLogger(__name__)

# Django dev server auto-reload 时避免在 reloader 进程中启动调度器
_skip_init = os.environ.get("RUN_MAIN") != "true"


def _close_db(func):
    """装饰器：任务执行后关闭数据库连接，防止连接泄漏"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        finally:
            connections.close_all()
        return result
    return wrapper


class SchedulerManager:
    """
    调度器管理类（单例）

    管理后台定时任务的生命周期。
    """

    _instance: Optional["SchedulerManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._scheduler: Optional[BackgroundScheduler] = None
        self._initialized = True

    @property
    def scheduler(self) -> BackgroundScheduler:
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler(
                jobstores={"default": MemoryJobStore()},
                timezone="Asia/Shanghai",
                job_defaults={"coalesce": True, "max_instances": 1},
            )
        return self._scheduler

    def start(self):
        """启动调度器"""
        if _skip_init:
            logger.info("跳过调度器初始化（reloader 进程）")
            return False
        try:
            self.scheduler.start()
            logger.info("调度器已启动")
            return True
        except SchedulerAlreadyRunningError:
            logger.warning("调度器已在运行中")
            return False

    def shutdown(self, wait: bool = False):
        """关闭调度器"""
        try:
            self.scheduler.shutdown(wait=wait)
            logger.info("调度器已关闭")
        except SchedulerNotRunningError:
            pass

    def add_job(
        self,
        job_id: str,
        func: str,
        cron_expr: str,
        *,
        replace: bool = True,
    ) -> bool:
        """
        添加定时任务

        Args:
            job_id:    任务唯一标识
            func:      可调用对象或 "module.path.function" 字符串
            cron_expr: 标准 5 段 cron 表达式（分 时 日 月 周）
            replace:   已存在时是否替换
        """
        if not self.scheduler.running:
            self.start()

        trigger = CronTrigger.from_crontab(cron_expr, timezone="Asia/Shanghai")

        # 支持 "module.path.function" 字符串
        if isinstance(func, str):
            parts = func.rsplit(".", 1)
            if len(parts) == 2:
                import importlib
                module = importlib.import_module(parts[0])
                func = getattr(module, parts[1])

        wrapped = _close_db(func)

        self.scheduler.add_job(
            func=wrapped,
            trigger=trigger,
            id=job_id,
            replace_existing=replace,
        )
        logger.info(f"已添加定时任务: {job_id} (cron={cron_expr})")
        return True

    def remove_job(self, job_id: str) -> bool:
        """移除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除定时任务: {job_id}")
            return True
        except Exception:
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停定时任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"已暂停任务: {job_id}")
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复定时任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"已恢复任务: {job_id}")
            return True
        except Exception:
            return False

    def trigger_job(self, job_id: str) -> bool:
        """手动触发一次任务执行"""
        try:
            job = self.scheduler.get_job(job_id)
            if job is None:
                return False
            # 直接调用包装函数
            job.func(*job.args, **job.kwargs)
            return True
        except Exception as e:
            logger.error(f"手动触发任务 {job_id} 失败: {e}")
            return False

    def get_jobs(self) -> list:
        """获取所有任务列表"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs

    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self.scheduler.running,
            "jobs": self.get_jobs(),
        }

    def is_running(self) -> bool:
        return self.scheduler.running


# 全局单例
scheduler_manager = SchedulerManager()


# ===== Cron 表达式验证工具 =====

def validate_cron(expr: str) -> Dict:
    """
    验证 cron 表达式是否合法

    Returns:
        {"valid": bool, "message": str, "human_readable": str}
    """
    if not expr or not expr.strip():
        return {"valid": False, "message": "表达式不能为空", "human_readable": ""}

    parts = expr.strip().split()
    if len(parts) != 5:
        return {"valid": False, "message": "需要 5 段：分 时 日 月 周", "human_readable": ""}

    field_names = ["分钟", "小时", "日", "月", "周"]
    for i, part in enumerate(parts):
        if not _is_valid_cron_field(part, i):
            return {
                "valid": False,
                "message": f"{field_names[i]} 字段无效: {part}",
                "human_readable": "",
            }

    return {
        "valid": True,
        "message": "合法",
        "human_readable": _cron_to_human(expr),
    }


def _is_valid_cron_field(value: str, field_index: int) -> bool:
    """验证单个 cron 字段"""
    # 每个字段使用合法的默认值（day/month 最小为 1）
    defaults = ["0", "0", "1", "1", "*"]
    test_fields = defaults.copy()
    test_fields[field_index] = value
    try:
        CronTrigger.from_crontab(" ".join(test_fields))
        return True
    except Exception:
        return False


def _cron_to_human(expr: str) -> str:
    """将 cron 表达式转为中文描述"""
    parts = expr.strip().split()
    minute, hour, day, month, dow = parts

    # 常见模式快速匹配
    if expr == "* * * * *":
        return "每分钟执行"
    if minute.startswith("*/") and hour == "*" and day == "*" and month == "*" and dow == "*":
        return f"每 {minute[2:]} 分钟执行"
    if hour.startswith("*/") and minute == "0" and day == "*" and month == "*" and dow == "*":
        return f"每 {hour[2:]} 小时执行"
    if minute == "0" and hour == "*" and day == "*" and month == "*" and dow == "*":
        return "每小时整点执行"
    if minute == "0" and hour == "0" and day == "*" and month == "*" and dow == "*":
        return "每天凌晨执行"
    if minute == "0" and hour == "0" and day == "*" and month == "*" and (dow == "1-5" or dow == "MON-FRI"):
        return "工作日凌晨执行"

    return f"cron: {expr}"
