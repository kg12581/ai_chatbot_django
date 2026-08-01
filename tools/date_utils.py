"""
日期时间处理工具
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


# 东八区时区
CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    """返回当前东八区时间"""
    return datetime.now(CST)


def to_cst(dt: datetime) -> datetime:
    """将任意时区时间转换为东八区"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CST)


def fmt(dt: datetime, pattern: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        return ""
    return to_cst(dt).strftime(pattern)


def parse(date_str: str, pattern: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析字符串为日期时间"""
    try:
        return datetime.strptime(date_str, pattern).replace(tzinfo=CST)
    except (ValueError, TypeError):
        return None


def time_ago(dt: datetime) -> str:
    """
    返回相对时间描述，如 "3分钟前"、"2小时前"、"1天前"
    """
    if dt is None:
        return ""
    dt = to_cst(dt)
    diff = now_cst() - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        return f"{seconds // 60}分钟前"
    elif seconds < 86400:
        return f"{seconds // 3600}小时前"
    elif seconds < 2592000:
        return f"{seconds // 86400}天前"
    else:
        return fmt(dt, "%Y-%m-%d")
