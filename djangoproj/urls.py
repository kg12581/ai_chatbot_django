"""
URL configuration for djangoproj project.
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from djangoapp.views import (
    home,
    chat_new,
    chat_detail,
    history,
    chat_stream,
    conversation_detail,
    chatbot_api,
)

urlpatterns = [
    # 页面路由
    path("", home, name="home"),
    path("chat/", chat_new, name="chat_new"),
    path("chat/<int:conv_id>/", chat_detail, name="chat_detail"),
    path("history/", history, name="history"),

    # API 路由
    path("chat/api/chat/stream/", chat_stream, name="chat_stream"),
    path("chat/api/conversations/<int:conv_id>/", conversation_detail, name="conversation_detail"),

    # 旧版 API（兼容 index.html）
    path("api/chatbot/", chatbot_api, name="chatbot_api"),

    # 抖音热搜
    path("api/", include("api.urls")),
]

# 开发环境下提供静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
