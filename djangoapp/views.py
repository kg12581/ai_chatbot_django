import json
import logging

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

        if not user_message:
            return JsonResponse({"error": "消息不能为空"}, status=400)

        # 获取或创建会话（按用户隔离，admin 也只能在自己的会话中聊天）
        if conversation_id:
            conversation = get_object_or_404(
                Conversation.objects.filter(user=request.user),
                id=conversation_id,
            )
        else:
            conversation = Conversation.objects.create(title="新对话", user=request.user)

        # 保存用户消息
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        # 如果是新会话，用第一条消息设置标题
        if conversation.title == "新对话":
            conversation.title = user_message[:50]
            conversation.save()

        # 构建历史消息
        history_messages = list(
            conversation.messages.values("role", "content")
        )

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
    """调用 DeepSeek 并逐块返回内容"""
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from chatbot import llm

    SYSTEM_PROMPT = (
        "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
        "回答尽量简洁明了。"
    )

    # 构建 langchain 消息列表
    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history_messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # 使用流式输出
    for chunk in llm.stream(lc_messages):
        if chunk.content:
            yield chunk.content


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


# ==================== 旧版 API（兼容） ====================


@csrf_exempt
def chatbot_api(request):
    """旧版非流式 chatbot API（兼容 index.html）"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            messages = data.get("messages", [])
            user_query = data.get("query", "")
            messages.append({"role": "user", "content": user_query})
            response = _call_deepseek_sync(messages)
            return JsonResponse({"messages": [
                {"type": "HumanMessage", "content": user_query, "role": None, "name": None, "additional_kwargs": {}},
                {"type": "AIMessage", "content": response, "role": None, "name": None, "additional_kwargs": {}},
            ]})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "POST request required"}, status=400)


def _call_deepseek_sync(messages):
    """同步调用 DeepSeek"""
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from chatbot import llm

    SYSTEM_PROMPT = (
        "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
        "回答尽量简洁明了。"
    )

    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in messages:
        if msg.get("role") == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    result = llm.invoke(lc_messages)
    return result.content
