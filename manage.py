#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django。您确定它已安装并且已添加到 PYTHONPATH 环境变量中吗？"
            "您是否忘记激活虚拟环境了？"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
