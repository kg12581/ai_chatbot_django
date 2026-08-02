"""
URL configuration for core project.
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from common.views import (
    home,
    chat_new,
    chat_detail,
    history,
    chat_stream,
    conversation_detail,
    upload_file,
)
from common.skill_views import (
    skills_dashboard,
    skill_create,
    skill_toggle,
    skill_delete,
    skill_update,
    skill_detail,
    mcp_server_create,
    mcp_server_toggle,
    mcp_server_delete,
    mcp_tool_toggle,
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
    path("chat/api/upload/", upload_file, name="upload_file"),
    path("chat/api/conversations/<int:conv_id>/", conversation_detail, name="conversation_detail"),

    # 抖音热搜
    path("api/", include("api.urls")),

    # 硬编码密钥扫描
    path("scanner/", include("scanner.urls")),

    # 埋点统计
    path("", include("analytics.urls")),

    # Skill 与 MCP 配置
    path("skills/", skills_dashboard, name="skills_dashboard"),
    path("skills/api/create/", skill_create, name="skill_create"),
    path("skills/api/<int:skill_id>/toggle/", skill_toggle, name="skill_toggle"),
    path("skills/api/<int:skill_id>/delete/", skill_delete, name="skill_delete"),
    path("skills/api/<int:skill_id>/update/", skill_update, name="skill_update"),
    path("skills/api/<int:skill_id>/", skill_detail, name="skill_detail"),
    path("skills/api/mcp/server/create/", mcp_server_create, name="mcp_server_create"),
    path("skills/api/mcp/server/<int:server_id>/toggle/", mcp_server_toggle, name="mcp_server_toggle"),
    path("skills/api/mcp/server/<int:server_id>/delete/", mcp_server_delete, name="mcp_server_delete"),
    path("skills/api/mcp/tool/<int:tool_id>/toggle/", mcp_tool_toggle, name="mcp_tool_toggle"),
]

# 开发环境下提供静态文件与上传文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
