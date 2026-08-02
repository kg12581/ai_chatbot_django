"""测试专用 Django 配置

测试时使用 SQLite 文件库（避免在共享的 MySQL 服务器上创建测试数据库）。
使用文件而非内存库，是为了让 Playwright 前端测试的 live_server
线程与主线程共享同一个数据库。
"""

import os
import tempfile

from core.settings import *  # noqa: F401,F403

# Playwright sync API 会在主线程注册 asyncio 事件循环，
# Django 默认拒绝同步 DB 调用；仅测试环境放行
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(tempfile.gettempdir(), "nocturne_test.sqlite3"),
        "TEST": {
            "NAME": os.path.join(tempfile.gettempdir(), "nocturne_test_db.sqlite3"),
        },
    }
}
