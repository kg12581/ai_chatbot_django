"""硬编码扫描 Web 视图测试"""

from unittest import mock

import pytest
from django.urls import reverse

from scanner import views as scanner_views
from scanner.models import ScanRun, SecretFinding
from tools.secret_scanner import ScanTimeoutError


@pytest.fixture
def users(db, django_user_model):
    admin = django_user_model.objects.create_user("admin", is_staff=True, is_superuser=True)
    normal = django_user_model.objects.create_user("normal")
    return admin, normal


@pytest.mark.django_db
def test_scanner_page_requires_login(client):
    assert client.get(reverse("scanner_home")).status_code == 302


@pytest.mark.django_db
def test_scanner_page(client, users):
    admin, _ = users
    client.force_login(admin)
    resp = client.get(reverse("scanner_home"))
    assert resp.status_code == 200
    assert "硬编码扫描" in resp.content.decode()


@pytest.mark.django_db
def test_non_staff_cannot_scan_custom_target(client, users):
    _, normal = users
    client.force_login(normal)
    resp = client.post(
        reverse("scanner_run"), data='{"target": "/tmp"}', content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_invalid_params_rejected(client, users):
    admin, _ = users
    client.force_login(admin)
    resp = client.post(
        reverse("scanner_run"),
        data='{"target": "", "max_seconds": "abc"}',
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_async_scan_flow(client, users):
    admin, _ = users
    client.force_login(admin)
    canned = {
        "files_scanned": 12,
        "findings": [{
            "rule_id": "test-rule", "rule_name": "测试规则", "severity": "high",
            "file_path": "x.py", "line_number": 1, "line_text": "含密钥行",
            "secret_preview": "sk-****", "entropy": 4.0,
        }],
    }
    with mock.patch("scanner.views.scan_target", return_value=canned), \
         mock.patch("threading.Thread.start", lambda self: self.run()), \
         mock.patch("django.db.connections.close_all"):
        resp = client.post(reverse("scanner_run"), data="{}", content_type="application/json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] and data["async"]

    run = ScanRun.objects.get(pk=data["run_id"])
    assert run.status == "finished"
    assert run.files_scanned == 12
    assert run.findings_count == 1
    assert SecretFinding.objects.filter(scan_run=run).count() == 1

    status = client.get(reverse("scanner_status", args=[run.pk])).json()
    assert status["run"]["status"] == "finished"


@pytest.mark.django_db
def test_worker_marks_failed_on_timeout(users):
    admin, _ = users
    run = ScanRun.objects.create(status="running")
    with mock.patch(
        "scanner.views.scan_target",
        side_effect=ScanTimeoutError("扫描超时（300 秒），已中止"),
    ), mock.patch("django.db.connections.close_all"):
        scanner_views._scan_worker(run.pk, "", 300, 50000)
    run.refresh_from_db()
    assert run.status == "failed"
    assert "超时" in run.error_message


@pytest.mark.django_db
def test_concurrent_scan_rejected(client, users):
    admin, _ = users
    ScanRun.objects.create(status="running")
    client.force_login(admin)
    resp = client.post(reverse("scanner_run"), data="{}", content_type="application/json")
    assert resp.status_code == 409


@pytest.mark.django_db
def test_update_finding_status(client, users):
    admin, _ = users
    run = ScanRun.objects.create(status="finished")
    finding = SecretFinding.objects.create(
        scan_run=run, rule_id="r", rule_name="规则", severity="high",
        file_path="a.py", secret_preview="***", status="open",
    )
    client.force_login(admin)
    resp = client.post(
        reverse("scanner_update_status", args=[finding.pk]),
        data='{"status": "false_positive"}', content_type="application/json",
    )
    assert resp.status_code == 200
    finding.refresh_from_db()
    assert finding.status == "false_positive"

    resp = client.post(
        reverse("scanner_update_status", args=[finding.pk]),
        data='{"status": "bogus"}', content_type="application/json",
    )
    assert resp.status_code == 400
