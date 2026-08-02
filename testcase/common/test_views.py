"""通用视图测试（首页/对话/历史/权限隔离）"""

import pytest
from django.urls import reverse

from common.models import Conversation


@pytest.mark.django_db
def test_home_requires_login(client):
    assert client.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_home_page(client, django_user_model):
    user = django_user_model.objects.create_user("u", password="pw")
    client.force_login(user)
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
def test_chat_new_creates_conversation(client, django_user_model):
    user = django_user_model.objects.create_user("u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("chat_new"))
    assert resp.status_code == 302
    assert Conversation.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_chat_detail_isolated_between_users(client, django_user_model):
    u1 = django_user_model.objects.create_user("u1", password="pw")
    u2 = django_user_model.objects.create_user("u2", password="pw")
    conv = Conversation.objects.create(title="私有会话", user=u1)

    client.force_login(u2)
    assert client.get(reverse("chat_detail", args=[conv.id])).status_code == 404

    client.force_login(u1)
    resp = client.get(reverse("chat_detail", args=[conv.id]))
    assert resp.status_code == 200
    assert "私有会话" in resp.content.decode()


@pytest.mark.django_db
def test_history_search(client, django_user_model):
    user = django_user_model.objects.create_user("u", password="pw")
    Conversation.objects.create(title="项目讨论", user=user)
    client.force_login(user)
    resp = client.get(reverse("history"), {"q": "项目"})
    assert resp.status_code == 200
    assert "项目讨论" in resp.content.decode()
