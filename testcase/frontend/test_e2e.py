"""前端端到端测试（Playwright + 系统 Chrome）

覆盖：登录页、登录流程、导航栏、对话页、抖音/微博热搜页、硬编码扫描页、移动端适配。
截图保存在 testcase/frontend/screenshots/。
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
TEST_PASSWORD = "e2e-pass-123"


def _save(page, name):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"), full_page=True)


def _login(page, live_server, user):
    page.goto(live_server.url + "/accounts/login/")
    page.fill('input[name="username"]', user.username)
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/")


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        try:
            browser_obj = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            # 无系统 Chrome 时回退到 Playwright 自带 Chromium
            browser_obj = p.chromium.launch(headless=True)
        yield browser_obj
        browser_obj.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    pg = context.new_page()
    pg.set_default_timeout(15000)
    yield pg
    context.close()


@pytest.fixture
def mobile_page(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    pg = context.new_page()
    pg.set_default_timeout(15000)
    yield pg
    context.close()


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user("e2e_user", password=TEST_PASSWORD)


@pytest.mark.django_db
def test_login_page_loads(page, live_server):
    page.goto(live_server.url + "/accounts/login/")
    assert "登录" in page.title()
    assert "Nocturne" in page.content()
    _save(page, "01-login")


@pytest.mark.django_db
def test_login_flow_and_nav(page, live_server, user):
    _login(page, live_server, user)
    nav = page.inner_text("nav")
    for item in ["历史记录", "抖音热搜", "微博热搜", "硬编码扫描", "Skill"]:
        assert item in nav, f"导航缺少: {item}"
    _save(page, "02-home")


@pytest.mark.django_db
def test_chat_page_creates_conversation(page, live_server, user):
    _login(page, live_server, user)
    page.goto(live_server.url + "/chat/")
    # chat_new 会创建会话并 302 重定向到 /chat/<id>/，goto 已等待最终加载
    assert "/chat/" in page.url
    assert page.url != live_server.url + "/chat/"
    body = page.inner_text("body")
    assert "新对话" in body or "对话" in body
    _save(page, "03-chat")


@pytest.mark.django_db
def test_douyin_hot_page(page, live_server, user):
    _login(page, live_server, user)
    page.goto(live_server.url + "/api/douyin/hot/")
    assert "抖音热搜榜" in page.inner_text("body")
    _save(page, "04-douyin-hot")


@pytest.mark.django_db
def test_weibo_hot_page(page, live_server, user):
    _login(page, live_server, user)
    page.goto(live_server.url + "/api/weibo/hot/")
    assert "微博热搜榜" in page.inner_text("body")
    _save(page, "05-weibo-hot")


@pytest.mark.django_db
def test_scanner_page(page, live_server, user):
    _login(page, live_server, user)
    page.goto(live_server.url + "/scanner/")
    body = page.inner_text("body")
    assert "硬编码扫描" in body
    assert "开始扫描" in body
    _save(page, "06-scanner")


@pytest.mark.django_db
def test_history_page(page, live_server, user):
    _login(page, live_server, user)
    page.goto(live_server.url + "/history/")
    assert "历史" in page.inner_text("body")
    _save(page, "07-history")


@pytest.mark.django_db
def test_mobile_viewport(mobile_page, live_server, user):
    _login(mobile_page, live_server, user)
    # 移动端不出现横向滚动
    overflow = mobile_page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"移动端出现横向溢出: {overflow}px"
    _save(mobile_page, "08-mobile-home")
