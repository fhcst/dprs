"""Security audit fix tests (change: security-audit-fixes)."""
import logging
import pytest
from datetime import date, datetime, timezone
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


# ─── Service-level fixtures ───────────────────────────────────────────────────

@pytest.fixture
async def service_db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_security_service")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from tasks.templates.models import TaskTemplate, TaskAssignment, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            CheckinConfig, CheckinRecord, DailyCheckinOverride,
        ],
    )
    yield database
    client.close()


@pytest.fixture
async def student(service_db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT
    u = User(
        username="stu",
        hashed_password=hash_password("pw"),
        display_name="S",
        permissions=int(STUDENT),
    )
    await u.insert()
    return u


@pytest.fixture
async def template(service_db):
    from tasks.templates.models import TaskTemplate
    t = TaskTemplate(
        name="Daily Log",
        description="",
        class_id="cls1",
        owner_id="owner1",
        fields=[],
    )
    await t.insert()
    return t


# ─── 4.1 Submission membership ────────────────────────────────────────────────

async def test_submit_task_non_member_raises_error(service_db, student, template):
    """Non-member student cannot submit — raises ValueError."""
    from tasks.submissions.service import submit_task
    with pytest.raises(ValueError, match="[Mm]ember"):
        await submit_task(
            template=template,
            class_id="cls1",
            student=student,
            submission_date=date.today(),
            field_values={},
        )


async def test_submit_task_member_succeeds(service_db, student, template):
    """Member student can submit normally."""
    from tasks.submissions.service import submit_task
    from core.classes.models import ClassMembership
    await ClassMembership(class_id="cls1", user_id=str(student.id), role="student").insert()
    sub = await submit_task(
        template=template,
        class_id="cls1",
        student=student,
        submission_date=date.today(),
        field_values={},
    )
    assert sub.student_id == str(student.id)


# ─── 4.2 Checkin membership ───────────────────────────────────────────────────

async def test_do_checkin_non_member_raises_error(service_db, student):
    """Non-member cannot check in — raises ValueError."""
    from tasks.checkin.service import set_global_config, do_checkin
    await set_global_config("cls1", list(range(7)), None, None)
    now = datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="[Mm]ember"):
        await do_checkin(student, "cls1", now)


async def test_do_checkin_member_succeeds(service_db, student):
    """Member student can check in normally."""
    from tasks.checkin.service import set_global_config, do_checkin
    from core.classes.models import ClassMembership
    await set_global_config("cls1", list(range(7)), None, None)
    await ClassMembership(class_id="cls1", user_id=str(student.id), role="student").insert()
    now = datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc)
    record = await do_checkin(student, "cls1", now)
    assert record.student_id == str(student.id)


# ─── 4.3 Checkin config ownership ────────────────────────────────────────────

@pytest.fixture
async def checkin_ownership_app():
    """Two teachers: teacher_a owns cls_a, teacher_b does not."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, CLASS_MANAGER
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.templates.models import TaskTemplate, TaskAssignment, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission

    client = AsyncMongoMockClient()
    db = client.get_database("test_checkin_ownership")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            CheckinConfig, CheckinRecord, DailyCheckinOverride,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
        ],
    )

    teacher_a = User(
        username="ta", hashed_password=hash_password("pw"), display_name="TA",
        permissions=int(TEACHER),
    )
    await teacher_a.insert()
    teacher_b = User(
        username="tb", hashed_password=hash_password("pw"), display_name="TB",
        permissions=int(TEACHER),
    )
    await teacher_b.insert()
    admin = User(
        username="adm", hashed_password=hash_password("pw"), display_name="Admin",
        permissions=int(CLASS_MANAGER),
    )
    await admin.insert()

    cls_a = Class(
        name="Class A", visibility="private",
        owner_id=str(teacher_a.id), invite_code="CLSA0001",
    )
    await cls_a.insert()
    await ClassMembership(class_id=str(cls_a.id), user_id=str(teacher_a.id), role="teacher").insert()
    # teacher_b is NOT a member of cls_a

    from fastapi import FastAPI
    from tasks.checkin.router import router as checkin_router
    from pages.router import router as pages_router

    app = FastAPI()
    app.include_router(pages_router)
    app.include_router(checkin_router)

    yield app, teacher_a, teacher_b, admin, cls_a
    client.close()


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


async def test_configure_checkin_wrong_teacher_returns_403(checkin_ownership_app):
    """Teacher B (not of cls_a) cannot configure cls_a's checkin — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, ta, tb, admin, cls_a = checkin_ownership_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls_a.id}/checkin-config",
            json={"active_weekdays": [0, 1]},
        )
    assert resp.status_code == 403


async def test_configure_checkin_own_teacher_returns_200(checkin_ownership_app):
    """Teacher A (of cls_a) can configure cls_a's checkin — 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, ta, tb, admin, cls_a = checkin_ownership_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(ta.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls_a.id}/checkin-config",
            json={"active_weekdays": [0, 1]},
        )
    assert resp.status_code == 200


async def test_configure_checkin_global_admin_returns_200(checkin_ownership_app):
    """Global admin can configure any class's checkin — 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import CLASS_MANAGER
    app, ta, tb, admin, cls_a = checkin_ownership_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(admin.id), int(CLASS_MANAGER)))
        resp = await ac.post(
            f"/classes/{cls_a.id}/checkin-config",
            json={"active_weekdays": [0, 1]},
        )
    assert resp.status_code == 200


async def test_create_override_wrong_teacher_returns_403(checkin_ownership_app):
    """Teacher B cannot create an override for cls_a — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, ta, tb, admin, cls_a = checkin_ownership_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls_a.id}/checkin-overrides",
            json={"date": "2026-04-01", "active": False},
        )
    assert resp.status_code == 403


async def test_checkin_config_page_wrong_teacher_returns_403(checkin_ownership_app):
    """Teacher B cannot access cls_a's checkin config page — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, ta, tb, admin, cls_a = checkin_ownership_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.get(
            f"/pages/teacher/classes/{cls_a.id}/checkin-config",
            follow_redirects=False,
        )
    assert resp.status_code == 403


# ─── 4.4 Discord webhook URL validation ───────────────────────────────────────

@pytest.fixture
async def classes_app():
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER

    client = AsyncMongoMockClient()
    db = client.get_database("test_classes_webhook")
    await init_beanie(database=db, document_models=[User, Class, ClassMembership])

    teacher = User(
        username="tc", hashed_password=hash_password("pw"), display_name="TC",
        permissions=int(TEACHER),
    )
    await teacher.insert()
    cls = Class(
        name="WH Class", visibility="public",
        owner_id=str(teacher.id), invite_code="WH001",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()

    from fastapi import FastAPI
    from core.classes.router import router as classes_router
    app = FastAPI()
    app.include_router(classes_router)

    yield app, teacher, cls
    client.close()


async def test_discord_webhook_valid_url_accepted(classes_app):
    """Valid discord.com webhook URL is accepted."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, teacher, cls = classes_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.patch(
            f"/classes/{cls.id}/discord-webhook",
            json={"webhook_url": "https://discord.com/api/webhooks/123/abc"},
        )
    assert resp.status_code == 200


async def test_discord_webhook_discordapp_url_accepted(classes_app):
    """discordapp.com webhook URL is also accepted."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, teacher, cls = classes_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.patch(
            f"/classes/{cls.id}/discord-webhook",
            json={"webhook_url": "https://discordapp.com/api/webhooks/456/xyz"},
        )
    assert resp.status_code == 200


async def test_discord_webhook_invalid_url_rejected(classes_app):
    """Non-Discord URL is rejected with 422."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, teacher, cls = classes_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.patch(
            f"/classes/{cls.id}/discord-webhook",
            json={"webhook_url": "https://evil.com/webhook"},
        )
    assert resp.status_code == 422


async def test_discord_webhook_empty_string_accepted(classes_app):
    """Empty string clears the webhook URL."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    app, teacher, cls = classes_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.patch(
            f"/classes/{cls.id}/discord-webhook",
            json={"webhook_url": ""},
        )
    assert resp.status_code == 200
    assert resp.json()["has_discord_webhook"] is False


# ─── 4.5 Setup password length ────────────────────────────────────────────────

@pytest.fixture
async def wizard_app():
    from core.users.models import User
    from core.system.models import SystemConfig
    import fakeredis.aioredis as fakeredis

    client = AsyncMongoMockClient()
    db = client.get_database("test_security_setup")
    await init_beanie(database=db, document_models=[User, SystemConfig])

    r = fakeredis.FakeRedis()

    from fastapi import FastAPI
    from core.system.router import router as system_router
    from pages.router import router as pages_router

    app = FastAPI()
    app.state.redis = r
    app.state.system_config = None
    app.include_router(pages_router)
    app.include_router(system_router)

    yield app, r
    await r.aclose()
    client.close()


async def test_setup_short_password_rejected(wizard_app):
    """Password shorter than 8 chars redirects to /setup with an error."""
    from httpx import AsyncClient, ASGITransport
    app, _ = wizard_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/setup",
            data={
                "site_name": "School",
                "admin_username": "admin",
                "admin_password": "short",
            },
            follow_redirects=False,
        )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "setup" in loc
    assert "error" in loc


async def test_setup_valid_password_succeeds(wizard_app):
    """Password 8+ characters proceeds successfully."""
    from httpx import AsyncClient, ASGITransport
    app, _ = wizard_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/setup",
            data={
                "site_name": "School",
                "admin_username": "admin",
                "admin_password": "secure123",
            },
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


# ─── 4.6 JWT secret warning ───────────────────────────────────────────────────

def test_jwt_warns_if_default_secret(caplog, monkeypatch):
    """Non-production with the default SESSION_SECRET logs a WARNING (does not raise)."""
    import core.auth.jwt as jwt_module
    from shared.environment import _DEFAULT_SECRET
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        jwt_module.check_secret_safety(secret=_DEFAULT_SECRET)
    assert any(
        "secret" in r.message.lower() or "default" in r.message.lower()
        for r in caplog.records
    )


def test_jwt_no_warning_if_custom_secret(caplog, monkeypatch):
    """A strong custom SESSION_SECRET does not log a WARNING."""
    import secrets
    import core.auth.jwt as jwt_module
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    strong_secret = secrets.token_hex(32)  # 64 hex chars
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        jwt_module.check_secret_safety(secret=strong_secret)
    assert caplog.records == []


# ─── 7.1 Dockerfile: FORWARDED_ALLOW_IPS must not be * ───────────────────────

def test_dockerfile_forwarded_allow_ips_not_wildcard():
    """Dockerfile must not set FORWARDED_ALLOW_IPS=* (CWE-16: IP spoofing via trusting all proxies)."""
    import pathlib
    dockerfile = pathlib.Path(__file__).parent.parent / "Dockerfile"
    content = dockerfile.read_text()
    assert "FORWARDED_ALLOW_IPS=*" not in content, (
        "Dockerfile sets FORWARDED_ALLOW_IPS=* which trusts ALL proxies and enables "
        "IP spoofing. Change to FORWARDED_ALLOW_IPS=\"\" so the default is no trusted proxies."
    )


# ─── 5.1 Docker-compose: MongoDB authentication ───────────────────────────────

@pytest.fixture
def compose():
    import pathlib, yaml
    path = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
    return yaml.safe_load(path.read_text())


def test_mongo_service_has_root_username(compose):
    """mongo service must configure MONGO_INITDB_ROOT_USERNAME."""
    env = compose["services"]["mongo"]["environment"]
    env_dict = {k: v for k, v in (e.split("=", 1) if "=" in e else (e, "") for e in env)} if isinstance(env, list) else env
    assert any("MONGO_INITDB_ROOT_USERNAME" in str(k) for k in env_dict), (
        "mongo service must set MONGO_INITDB_ROOT_USERNAME to enable authentication"
    )


def test_mongo_service_has_root_password(compose):
    """mongo service must configure MONGO_INITDB_ROOT_PASSWORD."""
    env = compose["services"]["mongo"]["environment"]
    env_dict = {k: v for k, v in (e.split("=", 1) if "=" in e else (e, "") for e in env)} if isinstance(env, list) else env
    assert any("MONGO_INITDB_ROOT_PASSWORD" in str(k) for k in env_dict), (
        "mongo service must set MONGO_INITDB_ROOT_PASSWORD to enable authentication"
    )


def test_app_mongo_url_includes_credentials(compose):
    """app service MONGO_URL must reference credential env vars."""
    env = compose["services"]["app"]["environment"]
    env_list = env if isinstance(env, list) else [f"{k}={v}" for k, v in env.items()]
    mongo_url_entries = [e for e in env_list if "MONGO_URL" in str(e)]
    assert mongo_url_entries, "app service must define MONGO_URL"
    mongo_url = str(mongo_url_entries[0])
    # Must not be a bare mongodb:// without credentials
    assert "@" in mongo_url or "MONGO_ROOT" in mongo_url or "MONGO_USERNAME" in mongo_url, (
        "MONGO_URL must include authentication credentials"
    )


# ─── 5.2 Docker-compose: Redis auth + port binding + mongo-express ────────────

def test_mongo_port_bound_to_localhost(compose):
    """MongoDB port must be bound to 127.0.0.1, not exposed publicly."""
    ports = compose["services"]["mongo"].get("ports", [])
    for p in ports:
        assert "127.0.0.1" in str(p), (
            f"MongoDB port '{p}' must be bound to 127.0.0.1, not exposed to all interfaces"
        )


def test_redis_port_bound_to_localhost(compose):
    """Redis port must be bound to 127.0.0.1, not exposed publicly."""
    ports = compose["services"]["redis"].get("ports", [])
    for p in ports:
        assert "127.0.0.1" in str(p), (
            f"Redis port '{p}' must be bound to 127.0.0.1, not exposed to all interfaces"
        )


def test_redis_service_has_requirepass(compose):
    """Redis service must be started with --requirepass."""
    redis_svc = compose["services"]["redis"]
    command = str(redis_svc.get("command", ""))
    assert "requirepass" in command, (
        "Redis service must use --requirepass to require authentication"
    )


def test_mongo_express_is_behind_profile_or_absent(compose):
    """mongo-express must be disabled by default (profiles) or removed entirely."""
    if "mongo-express" not in compose["services"]:
        return  # Removed — pass
    profiles = compose["services"]["mongo-express"].get("profiles", [])
    assert profiles, (
        "mongo-express must use Docker Compose profiles (e.g. profiles: [debug]) "
        "to prevent it from starting automatically in production"
    )
