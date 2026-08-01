"""Skill 与 MCP 配置视图。

提供独立的 Nocturne 主题配置页面，普通登录用户可：
- 查看所有 Skill，激活/取消激活
- 查看 MCP 服务器和工具列表
- 创建/编辑/删除 Skill（Prompt 模板）
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import View

from common.models import Skill, McpServer, McpTool

logger = logging.getLogger(__name__)


# ==================== 页面视图 ====================


@login_required
def skills_dashboard(request):
    """Skill 与 MCP 配置主页。"""
    skills = Skill.objects.all().order_by("-is_active", "-created_at")
    mcp_servers = McpServer.objects.all().order_by("-created_at")
    mcp_tools = McpTool.objects.all().order_by("category", "name")

    # 统计数据
    stats = {
        "skills_total": skills.count(),
        "skills_active": skills.filter(is_active=True).count(),
        "mcp_servers_total": mcp_servers.count(),
        "mcp_servers_enabled": mcp_servers.filter(enabled=True).count(),
        "mcp_tools_total": mcp_tools.count(),
        "mcp_tools_enabled": mcp_tools.filter(enabled=True).count(),
    }

    context = {
        "skills": skills,
        "mcp_servers": mcp_servers,
        "mcp_tools": mcp_tools,
        "stats": stats,
    }
    return render(request, "common/skills_dashboard.html", context)


# ==================== Skill 管理 API ====================


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def skill_create(request):
    """创建 Skill。"""
    try:
        data = json.loads(request.body)
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        system_prompt = (data.get("system_prompt") or "").strip()
        if not name or not system_prompt:
            return JsonResponse({"success": False, "error": "名称和 system prompt 必填"}, status=400)

        icon = (data.get("icon") or "sparkles").strip()
        color = (data.get("color") or "mint").strip()

        skill = Skill.objects.create(
            name=name[:100],
            description=description[:500],
            icon=icon[:50],
            color=color[:20],
            system_prompt=system_prompt,
            created_by=request.user,
        )
        return JsonResponse({
            "success": True,
            "id": skill.id,
            "message": f"Skill '{skill.name}' 已创建",
        })
    except Exception as e:
        logger.exception("创建 Skill 失败")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def skill_toggle(request, skill_id):
    """切换 Skill 激活状态。"""
    skill = get_object_or_404(Skill, id=skill_id)
    skill.is_active = not skill.is_active
    skill.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({
        "success": True,
        "is_active": skill.is_active,
        "message": f"Skill '{skill.name}' 已{'激活' if skill.is_active else '停用'}",
    })


@login_required
@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def skill_delete(request, skill_id):
    """删除 Skill。"""
    skill = get_object_or_404(Skill, id=skill_id)
    name = skill.name
    skill.delete()
    return JsonResponse({"success": True, "message": f"Skill '{name}' 已删除"})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def skill_update(request, skill_id):
    """更新 Skill。"""
    skill = get_object_or_404(Skill, id=skill_id)
    try:
        data = json.loads(request.body)
        if "name" in data:
            skill.name = (data["name"] or "").strip()[:100]
        if "description" in data:
            skill.description = (data["description"] or "").strip()[:500]
        if "system_prompt" in data:
            skill.system_prompt = (data["system_prompt"] or "").strip()
        if "icon" in data:
            skill.icon = (data["icon"] or "sparkles").strip()[:50]
        if "color" in data:
            skill.color = (data["color"] or "mint").strip()[:20]
        skill.save()
        return JsonResponse({"success": True, "message": f"Skill '{skill.name}' 已更新"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def skill_detail(request, skill_id):
    """获取 Skill 详情（JSON）。"""
    skill = get_object_or_404(Skill, id=skill_id)
    return JsonResponse({
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "icon": skill.icon,
        "color": skill.color,
        "system_prompt": skill.system_prompt,
        "is_active": skill.is_active,
    })


# ==================== MCP 服务器管理 API ====================


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mcp_server_create(request):
    """创建 MCP 服务器配置。"""
    try:
        data = json.loads(request.body)
        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "名称必填"}, status=400)

        server = McpServer.objects.create(
            name=name[:100],
            description=(data.get("description") or "").strip()[:500],
            transport=data.get("transport", "stdio"),
            command=(data.get("command") or "").strip()[:500],
            url=(data.get("url") or "").strip()[:500],
            env_vars=data.get("env_vars", ""),
            enabled=bool(data.get("enabled", False)),
        )
        return JsonResponse({
            "success": True,
            "id": server.id,
            "message": f"MCP 服务器 '{server.name}' 已创建",
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mcp_server_toggle(request, server_id):
    """切换 MCP 服务器启用状态。"""
    server = get_object_or_404(McpServer, id=server_id)
    server.enabled = not server.enabled
    server.save(update_fields=["enabled", "updated_at"])
    return JsonResponse({
        "success": True,
        "enabled": server.enabled,
        "message": f"MCP 服务器 '{server.name}' 已{'启用' if server.enabled else '禁用'}",
    })


@login_required
@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def mcp_server_delete(request, server_id):
    """删除 MCP 服务器。"""
    server = get_object_or_404(McpServer, id=server_id)
    name = server.name
    server.delete()
    return JsonResponse({"success": True, "message": f"MCP 服务器 '{name}' 已删除"})


# ==================== MCP 工具管理 API ====================


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mcp_tool_toggle(request, tool_id):
    """切换 MCP 工具启用状态。"""
    tool = get_object_or_404(McpTool, id=tool_id)
    tool.enabled = not tool.enabled
    tool.save(update_fields=["enabled", "updated_at"])
    return JsonResponse({
        "success": True,
        "enabled": tool.enabled,
        "message": f"工具 '{tool.name}' 已{'启用' if tool.enabled else '禁用'}",
    })


# ==================== 获取激活的 Skill/MCP（供 chatbot.py 调用） ====================


def get_active_skills_prompt():
    """获取所有激活 Skill 的 system prompt 拼接。

    Returns:
        str: 拼接后的 prompt 片段（可能为空）
    """
    active_skills = Skill.objects.filter(is_active=True)
    if not active_skills.exists():
        return ""
    parts = ["\n\n===== 已激活的 Skill ====="]
    for skill in active_skills:
        parts.append(f"\n【{skill.name}】\n{skill.system_prompt}")
    parts.append("===== Skill 结束 =====\n")
    return "\n".join(parts)


def get_active_mcp_tools_info():
    """获取已启用的 MCP 服务器和工具信息（用于展示给 AI）。"""
    servers = McpServer.objects.filter(enabled=True)
    tools = McpTool.objects.filter(enabled=True)
    info_parts = []
    if servers.exists():
        info_parts.append("已启用的 MCP 服务器:")
        for s in servers:
            info_parts.append(f"  - {s.name}: {s.description or s.command or s.url}")
    if tools.exists():
        info_parts.append("已启用的自建工具:")
        for t in tools:
            info_parts.append(f"  - {t.name}: {t.description} (路径: {t.func_path})")
    return "\n".join(info_parts) if info_parts else ""
