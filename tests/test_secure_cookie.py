"""Tests for secure=True cookie flag in production environment (task 2.1).

Verifies that set_cookie calls in both auth and pages routers pass
secure=True when FASTAPI_APP_ENVIRONMENT == "production", and do NOT
pass secure=True in non-production environments.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_production_helper():
    """Import the helper after monkeypatching env."""
    import core.auth.router as auth_router_mod
    return auth_router_mod._is_production()


# ---------------------------------------------------------------------------
# Unit tests: _is_production() helper
# ---------------------------------------------------------------------------

def test_is_production_returns_true_when_env_is_production(monkeypatch):
    """_is_production() returns True when FASTAPI_APP_ENVIRONMENT=production."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    import core.auth.router as auth_router_mod
    assert auth_router_mod._is_production() is True


def test_is_production_returns_false_when_env_is_development(monkeypatch):
    """_is_production() returns False when FASTAPI_APP_ENVIRONMENT=development."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "development")
    import core.auth.router as auth_router_mod
    assert auth_router_mod._is_production() is False


def test_is_production_returns_false_when_env_is_missing(monkeypatch):
    """_is_production() returns False when FASTAPI_APP_ENVIRONMENT is not set (default)."""
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    import core.auth.router as auth_router_mod
    assert auth_router_mod._is_production() is False


def test_is_production_returns_false_when_env_is_staging(monkeypatch):
    """_is_production() returns False for staging (only 'production' triggers secure)."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "staging")
    import core.auth.router as auth_router_mod
    assert auth_router_mod._is_production() is False


def test_pages_router_is_production_returns_true_when_env_is_production(monkeypatch):
    """pages.router._is_production() also returns True in production."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    import pages.router as pages_router_mod
    assert pages_router_mod._is_production() is True


def test_pages_router_is_production_returns_false_by_default(monkeypatch):
    """pages.router._is_production() returns False by default (no env var)."""
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    import pages.router as pages_router_mod
    assert pages_router_mod._is_production() is False


def test_is_production_returns_true_when_env_is_prod(monkeypatch):
    """The documented deployment value 'prod' is also treated as production.

    This is the load-bearing fix: docs/compose/entrypoint all use 'prod', which
    previously did NOT equal the literal 'production' and silently disabled Secure
    cookies. Both routers now delegate to the shared is_production() helper.
    """
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "prod")
    import core.auth.router as auth_router_mod
    import pages.router as pages_router_mod
    assert auth_router_mod._is_production() is True
    assert pages_router_mod._is_production() is True


# ---------------------------------------------------------------------------
# Integration tests: auth router /auth/login sets cookie with correct secure flag
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def register_auth_provider():
    """Register LocalAuthProvider for all tests in this module."""
    from core.auth.local_provider import LocalAuthProvider
    from extensions.protocols import AuthProvider
    from extensions.registry import registry, TestRegistry

    with TestRegistry() as reg:
        reg.register(AuthProvider, "local", LocalAuthProvider())
        yield


@pytest.fixture
async def auth_db():
    from mongomock_motor import AsyncMongoMockClient
    from beanie import init_beanie
    from core.users.models import User

    client = AsyncMongoMockClient()
    db = client.get_database("test_secure_cookie_auth")
    await init_beanie(database=db, document_models=[User])

    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT
    user = User(
        username="alice",
        hashed_password=hash_password("pass123"),
        display_name="Alice",
        permissions=int(STUDENT),
    )
    await user.insert()

    yield db, user
    client.close()


@pytest.fixture
async def pages_db():
    from mongomock_motor import AsyncMongoMockClient
    from beanie import init_beanie
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride, AttendanceCorrection
    from tasks.templates.models import TaskAssignment, TaskTemplate, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    from community.feed.models import FeedPost

    client = AsyncMongoMockClient()
    db = client.get_database("test_secure_cookie_pages")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            CheckinConfig, DailyCheckinOverride, CheckinRecord, AttendanceCorrection,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
            FeedPost,
        ],
    )

    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT
    user = User(
        username="alice_pages",
        hashed_password=hash_password("pass123"),
        display_name="Alice",
        permissions=int(STUDENT),
    )
    await user.insert()

    yield db, user
    client.close()


def _make_auth_app():
    from fastapi import FastAPI
    from core.auth.router import router as auth_router
    app = FastAPI()
    app.include_router(auth_router)
    return app


def _make_pages_app():
    from fastapi import FastAPI
    from core.auth.router import router as auth_router
    from pages.router import router as pages_router
    from gamification.badges.router import router as badges_router
    from gamification.leaderboard.router import router as leaderboard_router
    from gamification.points.router import router as points_router
    from tasks.checkin.router import router as checkin_router
    from tasks.submissions.router import router as submissions_router
    from tasks.templates.router import router as templates_router
    app = FastAPI()
    for r in [auth_router, pages_router, submissions_router,
              badges_router, leaderboard_router, points_router,
              checkin_router, templates_router]:
        app.include_router(r)
    return app


# ---------------------------------------------------------------------------
# auth router: /auth/login — secure=True in production
# ---------------------------------------------------------------------------

async def test_auth_login_sets_secure_cookie_in_production(auth_db, monkeypatch):
    """POST /auth/login in production env sets access_token cookie with Secure flag."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    app = _make_auth_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://example.com") as ac:
        response = await ac.post(
            "/auth/login",
            json={"username": "alice", "password": "pass123"},
        )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" in set_cookie_header, (
        "access_token cookie must include Secure flag in production"
    )


async def test_auth_login_sets_secure_cookie_when_env_is_prod(auth_db, monkeypatch):
    """POST /auth/login with FASTAPI_APP_ENVIRONMENT='prod' sets the Secure flag.

    Covers the documented production deployment value that previously failed the
    literal 'production' comparison.
    """
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "prod")
    app = _make_auth_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://example.com") as ac:
        response = await ac.post(
            "/auth/login",
            json={"username": "alice", "password": "pass123"},
        )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" in set_cookie_header, (
        "access_token cookie must include Secure flag when env is 'prod'"
    )


async def test_auth_login_does_not_set_secure_cookie_in_development(auth_db, monkeypatch):
    """POST /auth/login in development env does NOT set Secure flag on cookie."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "development")
    app = _make_auth_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        response = await ac.post(
            "/auth/login",
            json={"username": "alice", "password": "pass123"},
        )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" not in set_cookie_header, (
        "access_token cookie must NOT include Secure flag in development"
    )


async def test_auth_login_does_not_set_secure_cookie_with_no_env(auth_db, monkeypatch):
    """POST /auth/login with no FASTAPI_APP_ENVIRONMENT set does NOT set Secure flag."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    app = _make_auth_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        response = await ac.post(
            "/auth/login",
            json={"username": "alice", "password": "pass123"},
        )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" not in set_cookie_header, (
        "access_token cookie must NOT include Secure flag when env var is unset"
    )


# ---------------------------------------------------------------------------
# pages router: /pages/login — secure=True in production
# ---------------------------------------------------------------------------

async def test_pages_login_sets_secure_cookie_in_production(pages_db, monkeypatch):
    """POST /pages/login in production env sets access_token cookie with Secure flag."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    app = _make_pages_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://example.com") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice_pages", "password": "pass123"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" in set_cookie_header, (
        "access_token cookie must include Secure flag in production"
    )


async def test_pages_login_sets_secure_cookie_when_env_is_prod(pages_db, monkeypatch):
    """POST /pages/login with FASTAPI_APP_ENVIRONMENT='prod' sets the Secure flag."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "prod")
    app = _make_pages_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://example.com") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice_pages", "password": "pass123"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" in set_cookie_header, (
        "access_token cookie must include Secure flag when env is 'prod'"
    )


async def test_pages_login_does_not_set_secure_cookie_in_development(pages_db, monkeypatch):
    """POST /pages/login in development env does NOT set Secure flag on cookie."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "development")
    app = _make_pages_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice_pages", "password": "pass123"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" not in set_cookie_header, (
        "access_token cookie must NOT include Secure flag in development"
    )


async def test_pages_login_does_not_set_secure_cookie_with_no_env(pages_db, monkeypatch):
    """POST /pages/login with no FASTAPI_APP_ENVIRONMENT set does NOT set Secure flag."""
    from httpx import AsyncClient, ASGITransport
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    app = _make_pages_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice_pages", "password": "pass123"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header, "access_token cookie must be set"
    assert "Secure" not in set_cookie_header, (
        "access_token cookie must NOT include Secure flag when env var is unset"
    )
