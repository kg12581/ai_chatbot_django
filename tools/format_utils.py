"""
数据格式化工具
"""

from typing import Union


def number(num: Union[int, float, str], decimals: int = 0) -> str:
    """
    数字千分位格式化

    Examples:
        1234567 → "1,234,567"
        1234567.89, 2 → "1,234,567.89"
    """
    try:
        num = float(num)
    except (ValueError, TypeError):
        return str(num) if num else "0"
    if decimals == 0:
        return f"{int(num):,}"
    return f"{num:,.{decimals}f}"


def file_size(size_bytes: int) -> str:
    """
    文件大小格式化

    Examples:
        1024 → "1.0 KB"
        1048576 → "1.0 MB"
    """
    if not size_bytes or size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def hot_value(value: int) -> str:
    """
    热度值格式化（万/亿）

    Examples:
        9823000 → "982.3万"
        120000000 → "1.2亿"
    """
    if not value:
        return "0"
    if value >= 100000000:
        return f"{value / 100000000:.1f}亿"
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(value)


def duration(seconds: int) -> str:
    """
    时长格式化

    Examples:
        65 → "1分5秒"
        3725 → "1小时2分5秒"
    """
    if not seconds or seconds < 0:
        return "0秒"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")
    return "".join(parts)


def percent(value: float, total: float, decimals: int = 1) -> str:
    """
    百分比格式化

    Examples:
        3, 7 → "42.9%"
    """
    if not total:
        return "0%"
    return f"{value / total * 100:.{decimals}f}%"
