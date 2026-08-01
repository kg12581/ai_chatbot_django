import json
import logging
import os
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from .models import Conversation, Message

logger = logging.getLogger(__name__)


def _visible_conversations(user):
    """返回该用户可见的会话 QuerySet。

    规则：
      - 超级用户（admin）可以查看所有会话
      - 普通用户只能查看自己的会话
    """
    if user.is_superuser:
        return Conversation.objects.all()
    return Conversation.objects.filter(user=user)


# ==================== 页面视图 ====================


@login_required
def home(request):
    """首页"""
    conversation_count = _visible_conversations(request.user).count()
    return render(request, "home.html", {
        "conversation_count": conversation_count,
    })


@login_required
def chat_new(request):
    """新建对话 - 重定向到新会话"""
    conv = Conversation.objects.create(title="新对话", user=request.user)
    return redirect("chat_detail", conv_id=conv.id)


@login_required
def chat_detail(request, conv_id):
    """对话详情页"""
    # 普通用户访问他人会话会 404；admin 可访问任意会话
    conversation = get_object_or_404(
        Conversation.objects.filter(user=request.user) if not request.user.is_superuser
        else Conversation.objects.all(),
        id=conv_id,
    )
    conversations = _visible_conversations(request.user)[:20]
    messages = list(conversation.messages.values("role", "content"))
    messages_json = json.dumps(messages, ensure_ascii=False)

    return render(request, "chat.html", {
        "conversations": conversations,
        "current_conversation": conversation,
        "messages": messages,
        "messages_json": messages_json,
    })


@login_required
def history(request):
    """历史记录页"""
    query = request.GET.get("q", "").strip()
    qs = _visible_conversations(request.user)
    if query:
        conversations = qs.filter(title__icontains=query)
    else:
        conversations = qs
    return render(request, "history.html", {
        "conversations": conversations,
        "query": query,
    })


# ==================== API 视图 ====================


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def chat_stream(request):
    """SSE 流式对话接口"""
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")
        attachments = data.get("attachments", [])  # [{"name", "type", "content", "size"}]

        if not user_message and not attachments:
            return JsonResponse({"error": "消息不能为空"}, status=400)

        # 获取或创建会话（按用户隔离，admin 也只能在自己的会话中聊天）
        if conversation_id:
            conversation = get_object_or_404(
                Conversation.objects.filter(user=request.user),
                id=conversation_id,
            )
        else:
            conversation = Conversation.objects.create(title="新对话", user=request.user)

        # 组装展示用消息（含附件信息）
        display_message = user_message
        if attachments:
            attach_info = []
            for a in attachments:
                if a.get("type") == "image":
                    attach_info.append(f"[图片: {a.get('name', '未命名')}]")
                else:
                    attach_info.append(f"[文件: {a.get('name', '未命名')}]")
            display_message = (user_message + "\n\n" + "\n".join(attach_info)).strip() if user_message else "\n".join(attach_info)

        # 保存用户消息
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=display_message,
        )

        # 如果是新会话，用第一条消息设置标题
        if conversation.title == "新对话":
            conversation.title = (user_message or attachments[0]["name"])[:50]
            conversation.save()

        # 构建历史消息（注入附件内容到最后一条用户消息）
        history_messages = list(
            conversation.messages.values("role", "content")
        )
        if attachments and history_messages:
            augmented = _augment_with_attachments(user_message, attachments)
            history_messages[-1]["content"] = augmented

        def event_stream():
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation.id})}\n\n"

            full_response = ""
            try:
                for chunk in _call_deepseek(history_messages):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

                # 保存 AI 回复
                Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=full_response,
                )
                conversation.save()  # 更新 updated_at

            except Exception as e:
                logger.exception("DeepSeek 调用失败")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

            # 发送结束事件
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation.id})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    except Exception as e:
        logger.exception("chat_stream 异常")
        return JsonResponse({"error": str(e)}, status=500)


def _call_deepseek(history_messages):
    """调用 Agent 工作流并逐块返回内容（支持 SSH 工具和 RAG 检索）。"""
    from chatbot import stream_chat

    for chunk in stream_chat(history_messages):
        yield chunk


def _augment_with_attachments(user_message, attachments):
    """将附件内容拼接到用户消息中，供 AI 分析。"""
    parts = []
    if user_message:
        parts.append(user_message)

    for a in attachments:
        name = a.get("name", "未命名")
        ftype = a.get("type", "file")
        content = a.get("content", "")

        if ftype == "image":
            parts.append(f"\n[图片: {name}]（图片已接收，如需分析请描述其内容）")
        else:
            if content:
                if len(content) > 8000:
                    content = content[:8000] + f"\n... (已截断，共 {len(content)} 字符)"
                parts.append(f"\n[文件: {name}]\n```\n{content}\n```")
            else:
                parts.append(f"\n[文件: {name}]（空文件或无法读取内容）")

    return "\n".join(parts)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """文件上传接口。返回文件信息（名称、类型、内容、大小）。"""
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"success": False, "error": "未找到上传文件"}, status=400)

    if upload.size > 10 * 1024 * 1024:
        return JsonResponse({"success": False, "error": "文件超过 10MB 限制"}, status=400)

    name = upload.name
    ext = Path(name).suffix.lower()
    size = upload.size

    readable_exts = getattr(settings, "UPLOAD_READABLE_EXTS", set())
    image_exts = getattr(settings, "UPLOAD_IMAGE_EXTS", set())

    if ext in image_exts:
        # 图片：保存到 media 目录
        media_dir = Path(settings.MEDIA_ROOT) / "uploads"
        media_dir.mkdir(parents=True, exist_ok=True)
        import time
        safe_name = f"{int(time.time())}_{name}"
        file_path = media_dir / safe_name
        with open(file_path, "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)
        return JsonResponse({
            "success": True,
            "name": name,
            "type": "image",
            "size": size,
            "url": f"{settings.MEDIA_URL}uploads/{safe_name}",
            "content": "",
        })

    elif ext in readable_exts:
        # 文本类：读取内容
        try:
            raw = upload.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("gbk", errors="replace")
            if len(content) > 30000:
                content = content[:30000] + f"\n... (已截断，共 {len(content)} 字符)"
            return JsonResponse({
                "success": True,
                "name": name,
                "type": "file",
                "size": size,
                "content": content,
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": f"读取失败: {e}"}, status=500)

    else:
        return JsonResponse({
            "success": False,
            "error": f"不支持的文件类型: {ext}"
        }, status=400)


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def conversation_detail(request, conv_id):
    """删除会话（普通用户只能删除自己的会话）"""
    conversation = get_object_or_404(
        Conversation.objects.filter(user=request.user) if not request.user.is_superuser
        else Conversation.objects.all(),
        id=conv_id,
    )
    conversation.delete()
    return JsonResponse({"ok": True})
