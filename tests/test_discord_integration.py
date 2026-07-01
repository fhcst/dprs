"""Tests for discord-integration capability."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


# ─── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_discord")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from tasks.templates.models import TaskTemplate, TaskAssignment
    from tasks.submissions.models import TaskSubmission
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership, TaskTemplate, TaskAssignment, TaskSubmission],
    )
    yield database
    client.close()


@pytest.fixture
async def teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    u = User(
        username="teach",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await u.insert()
    return u


@pytest.fixture
async def cls(db, teacher):
    from core.classes.models import Class
    c = Class(
        name="Python 101",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="TEST1234",
    )
    await c.insert()
    return c


# ─── Task 1.1: Class model - discord_webhook_url ──────────────────────────────

async def test_class_discord_webhook_url_defaults_to_none(db, teacher):
    from core.classes.models import Class
    c = Class(
        name="Test Class",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="ABCD",
    )
    assert c.discord_webhook_url is None


async def test_class_discord_webhook_url_can_be_set(db, teacher):
    from core.classes.models import Class
    c = Class(
        name="Test Class",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="ABCD",
        discord_webhook_url="https://discord.com/api/webhooks/123/abc",
    )
    await c.insert()
    fetched = await Class.get(c.id)
    assert fetched.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"


# ─── Tasks 5.1: send_task_embed unit tests ───────────────────────────────────

async def test_send_task_embed_posts_correct_payload():
    """send_task_embed sends a POST with embed format to the given webhook URL."""
    from integrations.discord.service import send_task_embed

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("integrations.discord.service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await send_task_embed(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            task_name="每日練習",
            description="請完成今日作業",
            date="2026-03-21",
        )

    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["json"]
    embeds = payload["embeds"]
    assert len(embeds) == 1
    embed = embeds[0]
    assert embed["title"] == "每日練習 — 2026-03-21"
    assert embed["color"] == 0x7C3AED


async def test_send_task_embed_truncates_description():
    """Description longer than 200 chars is truncated."""
    from integrations.discord.service import send_task_embed

    long_desc = "X" * 300
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("integrations.discord.service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await send_task_embed(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            task_name="Task",
            description=long_desc,
            date=None,
        )

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs.kwargs["json"]
    embed = payload["embeds"][0]
    assert len(embed["description"]) <= 203  # 200 + "..."


async def test_send_task_embed_http_failure_does_not_raise():
    """HTTP failure is swallowed and logged, not re-raised."""
    import httpx
    from integrations.discord.service import send_task_embed

    with patch("integrations.discord.service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_cls.return_value = mock_client

        # Must not raise
        await send_task_embed(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            task_name="Task",
            description="desc",
            date="2026-03-21",
        )


# ─── Tasks 5.2 + 5.3: template assignment integration tests ──────────────────

def _make_app():
    from core.auth.router import router as auth_router
    from core.classes.router import router as classes_router
    from tasks.templates.router import router as templates_router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(classes_router)
    app.include_router(templates_router)
    return app


@pytest.fixture
async def http_db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_discord_http")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from tasks.templates.models import TaskTemplate, TaskAssignment, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership, TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission],
    )
    yield database
    client.close()


@pytest.fixture
def register_auth_provider():
    from core.auth.local_provider import LocalAuthProvider
    from extensions.protocols import AuthProvider
    from extensions.registry import TestRegistry
    with TestRegistry() as reg:
        reg.register(AuthProvider, "local", LocalAuthProvider())
        yield


@pytest.fixture
async def http_client(http_db, register_auth_provider, teacher_token):
    from httpx import ASGITransport, AsyncClient
    user, token = teacher_token
    app = _make_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"access_token": token},
    ) as client:
        yield client


@pytest.fixture
async def teacher_token(http_db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    from core.auth.jwt import create_access_token
    u = User(
        username="teacherhttp",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await u.insert()
    return u, create_access_token(str(u.id), int(TEACHER))


@pytest.fixture
async def cls_with_webhook(http_db, teacher_token):
    from core.classes.models import Class, ClassMembership
    user, _ = teacher_token
    c = Class(
        name="Discord Class",
        visibility="public",
        owner_id=str(user.id),
        invite_code="DISC1234",
        discord_webhook_url="https://discord.com/api/webhooks/999/secret",
    )
    await c.insert()
    await ClassMembership(class_id=str(c.id), user_id=str(user.id), role="teacher").insert()
    return c


@pytest.fixture
async def cls_without_webhook(http_db, teacher_token):
    from core.classes.models import Class, ClassMembership
    user, _ = teacher_token
    c = Class(
        name="No Discord Class",
        visibility="public",
        owner_id=str(user.id),
        invite_code="NODC1234",
    )
    await c.insert()
    await ClassMembership(class_id=str(c.id), user_id=str(user.id), role="teacher").insert()
    return c


@pytest.fixture
async def template_with_webhook(http_db, cls_with_webhook, teacher_token):
    from tasks.templates.models import TaskTemplate, FieldDefinition as FieldDefinition
    user, _ = teacher_token
    t = TaskTemplate(
        name="Daily Practice",
        description="Complete your daily exercises",
        class_id=str(cls_with_webhook.id),
        fields=[FieldDefinition(name="content", field_type="text", required=True)],
        owner_id=str(user.id),
    )
    await t.insert()
    return t


@pytest.fixture
async def template_without_webhook(http_db, cls_without_webhook, teacher_token):
    from tasks.templates.models import TaskTemplate, FieldDefinition as FieldDefinition
    user, _ = teacher_token
    t = TaskTemplate(
        name="Daily Practice 2",
        description="No webhook class",
        class_id=str(cls_without_webhook.id),
        fields=[FieldDefinition(name="content", field_type="text", required=True)],
        owner_id=str(user.id),
    )
    await t.insert()
    return t


async def test_assign_with_sync_discord_sends_message(
    http_client, cls_with_webhook, template_with_webhook
):
    """When sync_discord=True and class has webhook URL, Discord message is sent."""
    with patch("tasks.templates.router.discord_send_task_embed") as mock_send:
        mock_send.return_value = None
        resp = await http_client.post(
            f"/classes/{cls_with_webhook.id}/schedule-rules",
            json={
                "template_id": str(template_with_webhook.id),
                "schedule_type": "once",
                "date": "2026-03-21",
                "sync_discord": True,
            },
        )
    assert resp.status_code == 201
    mock_send.assert_called_once()


async def test_assign_without_sync_discord_no_message(
    http_client, cls_with_webhook, template_with_webhook
):
    """When sync_discord=False, no Discord message is sent."""
    with patch("tasks.templates.router.discord_send_task_embed") as mock_send:
        mock_send.return_value = None
        resp = await http_client.post(
            f"/classes/{cls_with_webhook.id}/schedule-rules",
            json={
                "template_id": str(template_with_webhook.id),
                "schedule_type": "once",
                "date": "2026-03-22",
                "sync_discord": False,
            },
        )
    assert resp.status_code == 201
    mock_send.assert_not_called()


async def test_assign_no_webhook_url_no_message(
    http_client, cls_without_webhook, template_without_webhook
):
    """When class has no webhook URL, no Discord message is sent even if sync_discord=True."""
    with patch("tasks.templates.router.discord_send_task_embed") as mock_send:
        mock_send.return_value = None
        resp = await http_client.post(
            f"/classes/{cls_without_webhook.id}/schedule-rules",
            json={
                "template_id": str(template_without_webhook.id),
                "schedule_type": "once",
                "date": "2026-03-23",
                "sync_discord": True,
            },
        )
    assert resp.status_code == 201
    mock_send.assert_not_called()


# ─── Task 5.3: Discord failure does not block task assignment ─────────────────

async def test_assign_succeeds_despite_discord_failure(
    http_client, cls_with_webhook, template_with_webhook
):
    """Task assignment succeeds even if Discord send raises an exception."""
    import httpx

    async def failing_send(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    with patch("tasks.templates.router.discord_send_task_embed", side_effect=failing_send):
        resp = await http_client.post(
            f"/classes/{cls_with_webhook.id}/schedule-rules",
            json={
                "template_id": str(template_with_webhook.id),
                "schedule_type": "once",
                "date": "2026-03-24",
                "sync_discord": True,
            },
        )
    assert resp.status_code == 201


# ─── Task 4.2 + 4.3: PATCH /classes/<id>/discord-webhook ─────────────────────

async def test_patch_discord_webhook_saves_url(http_client, cls_without_webhook):
    """PATCH /classes/<id>/discord-webhook saves the URL."""
    resp = await http_client.patch(
        f"/classes/{cls_without_webhook.id}/discord-webhook",
        json={"webhook_url": "https://discord.com/api/webhooks/123/abc"},
    )
    assert resp.status_code == 200
    from core.classes.models import Class
    cls = await Class.get(cls_without_webhook.id)
    assert cls.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"


async def test_patch_discord_webhook_empty_string_clears_url(http_client, cls_with_webhook):
    """Sending empty string for webhook_url clears it to None."""
    resp = await http_client.patch(
        f"/classes/{cls_with_webhook.id}/discord-webhook",
        json={"webhook_url": ""},
    )
    assert resp.status_code == 200
    from core.classes.models import Class
    cls = await Class.get(cls_with_webhook.id)
    assert cls.discord_webhook_url is None
