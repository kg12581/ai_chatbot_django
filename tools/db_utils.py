"""
数据库操作辅助工具
"""

import logging
from typing import List, Dict, Type
from django.db import models, transaction

logger = logging.getLogger(__name__)


def bulk_upsert(
    model: Type[models.Model],
    data: List[Dict],
    *,
    unique_fields: List[str],
    batch_size: int = 500,
) -> Dict:
    """
    批量插入或更新（基于 unique_fields 判断是否存在）

    Args:
        model:         Django 模型类
        data:          字典列表
        unique_fields: 用于判断唯一性的字段名列表
        batch_size:    每批处理数量

    Returns:
        {"created": N, "updated": N}
    """
    created = 0
    updated = 0

    with transaction.atomic():
        for item in data:
            lookup = {f: item.get(f) for f in unique_fields}
            obj, was_created = model.objects.update_or_create(
                defaults=item,
                **lookup,
            )
            if was_created:
                created += 1
            else:
                updated += 1

    logger.info(f"{model.__name__} upsert 完成: 新建 {created}, 更新 {updated}")
    return {"created": created, "updated": updated}


def model_to_dict(instance: models.Model, exclude: List[str] = None) -> Dict:
    """
    将模型实例转为字典（包含所有字段，排除指定字段）
    """
    exclude = exclude or []
    data = {}
    for field in instance._meta.fields:
        if field.name in exclude:
            continue
        value = getattr(instance, field.name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        data[field.name] = value
    return data


def queryset_to_list(qs, exclude: List[str] = None) -> List[Dict]:
    """将 QuerySet 转为字典列表"""
    return [model_to_dict(obj, exclude) for obj in qs]


def clear_table(model: Type[models.Model]) -> int:
    """
    清空表数据（谨慎使用！）

    Returns:
        删除的记录数
    """
    count = model.objects.count()
    model.objects.all().delete()
    logger.warning(f"已清空 {model.__name__} 表，删除 {count} 条记录")
    return count


def get_or_none(model: Type[models.Model], **kwargs) -> models.Model:
    """查询记录，不存在则返回 None"""
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None
