"""硬编码扫描引擎测试（无数据库依赖）"""

import pytest

from tools.secret_scanner import (
    ScanTimeoutError,
    _redact,
    scan_repository,
    scan_target,
    scan_text,
    shannon_entropy,
)


def test_shannon_entropy():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") == 2.0


def test_django_secret_key_detected():
    findings = scan_text('SECRET_KEY = "django-insecure-abc123XYZ"', "settings.py")
    assert any(f["rule_id"] == "django-secret-key" for f in findings)


def test_deepseek_key_detected():
    # 假密钥拆开拼接，避免触发 GitHub 密钥推送保护（sk- 完整格式会被识别为真实 Key）
    fake_key = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    findings = scan_text('DEEPSEEK_API_KEY = "' + fake_key + '"', "x.py")
    assert any(f["rule_id"] == "deepseek-api-key" for f in findings)


def test_password_placeholder_allowed():
    assert scan_text('PASSWORD = "your_password"', "x.py") == []


def test_low_entropy_not_flagged():
    assert scan_text('PASSWORD = "11111111"', "x.py") == []


def test_line_text_is_redacted():
    findings = scan_text('PASSWORD = "Admin@123456"', "settings.py")
    assert findings
    assert "Admin@123456" not in findings[0]["line_text"]
    assert "*" in findings[0]["line_text"]
    assert findings[0]["secret_preview"] != "Admin@123456"


def test_redact():
    assert "abcdef" not in _redact("sk-" + "abcdefghijklmnopqrstuvwxyz")
    assert _redact("short") == "*****"


def test_repository_timeout(tmp_path):
    (tmp_path / "a.txt").write_text('PASSWORD = "Admin@123456"', encoding="utf-8")
    with pytest.raises(ScanTimeoutError):
        scan_repository(str(tmp_path), max_seconds=0)


def test_repository_scan(tmp_path):
    (tmp_path / "a.txt").write_text('token = "randomtoken123456789"', encoding="utf-8")
    (tmp_path / "b.py").write_text("ok = 1", encoding="utf-8")
    result = scan_repository(str(tmp_path))
    assert result["files_scanned"] == 2
    assert len(result["findings"]) == 1


def test_scan_target_invalid_url():
    with pytest.raises(ValueError):
        scan_target("https://user:pass@github.com/x/y.git")


def test_scan_target_forbidden_root():
    with pytest.raises(ValueError):
        scan_target("/")


def test_scan_target_missing_dir():
    with pytest.raises(ValueError):
        scan_target("/no/such/dir")


def test_scan_target_local_dir(tmp_path, monkeypatch):
    # macOS 的临时目录位于 /private/var 下，测试时放行 /private
    import tools.secret_scanner as secret_scanner
    monkeypatch.setattr(
        secret_scanner, "FORBIDDEN_SCAN_ROOTS",
        [p for p in secret_scanner.FORBIDDEN_SCAN_ROOTS if p != "/private"],
    )
    (tmp_path / "a.txt").write_text('token = "randomtoken123456789"', encoding="utf-8")
    result = scan_target(str(tmp_path))
    assert result["files_scanned"] == 1
    assert len(result["findings"]) == 1
