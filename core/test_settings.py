"""测试专用 Django 配置

测试时使用 SQLite 内存库，避免在共享的 MySQL 服务器上创建测试数据库。
"""

from core.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
