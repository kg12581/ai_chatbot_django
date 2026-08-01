"""
URL configuration for core project.
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

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
    # Django Admin 后台
    path("admin/", admin.site.urls),

    # 认证（登录/登出/密码重置，邮件功能）
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/password_reset/", auth_views.PasswordResetView.as_view(email_template_name="registration/password_reset_email.txt", subject_template_name="registration/password_reset_subject.txt"), name="password_reset"),
    path("accounts/password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

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
