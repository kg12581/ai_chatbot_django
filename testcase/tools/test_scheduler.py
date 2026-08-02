"""定时调度工具测试"""

from tools.scheduler import validate_cron


def test_valid_cron():
    for expr in ["* * * * *", "0 * * * *", "*/30 * * * *", "0 0 * * MON-FRI"]:
        assert validate_cron(expr)["valid"], expr


def test_invalid_cron():
    for expr in ["", "bad", "0 * * *", "* * * * * *", "60 * * * *", "0 24 * * *", "* * 32 * *"]:
        assert not validate_cron(expr)["valid"], expr


def test_human_readable():
    assert "每 30 分钟" in validate_cron("*/30 * * * *")["human_readable"]
