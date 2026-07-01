"""Tests for admin system config API endpoints (Task 5.5)."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_admin_system")
    from core.users.models import User
    from core.system.models import SystemConfig
    await init_beanie(database=database, document_models=[User, SystemConfig])
    yield database
    client.close()


@pytest.fixture
def app(db):
    from fastapi import FastAPI
    from core.system.router import router
    app = FastAPI()
    app.include_router(router)
    # Simulate app.state.system_config being set after setup
    from core.system.models import SystemConfig
    app.state.system_config = MagicMock(spec=SystemConfig)
    app.state.system_config.site_name = "Test Site"
    app.state.system_config.admin_email = "admin@test.com"
    return app


async def _make_user(permissions_val: int, username: str = "admin"):
    from core.auth.password import hash_password
    from core.auth.jwt import create_access_token
    from core.users.models import User
    user = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name=username,
        permissions=permissions_val,
    )
    await user.insert()
    return create_access_token(user_id=str(user.id), permissions=permissions_val)


async def test_get_system_config_returns_site_name(db, app):
    """GET /admin/system must return site_name and admin_email."""
    from core.auth.permissions import SITE_ADMIN
    token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/system")
    assert resp.status_code == 200
    data = resp.json()
    assert "site_name" in data
    assert "admin_email" in data


async def test_get_system_config_requires_read_system(db, app):
    """GET /admin/system must return 403 without READ_SYSTEM."""
    from core.auth.permissions import STUDENT
    token = await _make_user(int(STUDENT), username="student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/system")
    assert resp.status_code == 403


async def test_put_system_config_updates_site_name(db, app):
    """PUT /admin/system must update site_name in MongoDB and in-memory state."""
    from core.auth.permissions import SITE_ADMIN
    from core.system.models import SystemConfig
    # Insert a real SystemConfig in DB
    config = SystemConfig(site_name="Old Name", admin_email="admin@test.com")
    await config.insert()
    app.state.system_config = config

    token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put("/admin/system", json={"site_name": "New Name", "admin_email": "admin@test.com"})
    assert resp.status_code == 200
    assert resp.json()["site_name"] == "New Name"
    # Verify in-memory state updated
    assert app.state.system_config.site_name == "New Name"


async def test_put_system_config_requires_write_system(db, app):
    """PUT /admin/system must return 403 without WRITE_SYSTEM."""
    from core.auth.permissions import STUDENT
    token = await _make_user(int(STUDENT), username="student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put("/admin/system", json={"site_name": "X", "admin_email": "x@x.com"})
    assert resp.status_code == 403


async def test_post_setup_catch_all_does_not_leak_internal_error(db):
    """POST /setup catch-all handler must not expose internal exception details in redirect URL."""
    from fastapi import FastAPI
    from core.system.router import router
    from unittest.mock import AsyncMock, patch

    setup_app = FastAPI()
    setup_app.include_router(router)
    # No system_config → not yet configured
    setup_app.state.system_config = None
    setup_app.state.redis = AsyncMock()

    # Force SystemConfig.insert to raise an exception with a sensitive internal message
    sensitive_message = "MongoError: connection refused to internal-host:27017"

    async with AsyncClient(transport=ASGITransport(app=setup_app), base_url="http://test") as ac:
        with patch("core.system.models.SystemConfig.insert", side_effect=Exception(sensitive_message)):
            resp = await ac.post(
                "/setup",
                data={
                    "site_name": "Test",
                    "admin_username": "admin",
                    "admin_password": "securepassword",
                },
                follow_redirects=False,
            )

    # Should redirect to setup page on error
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    # The sensitive internal message must NOT appear in the redirect URL
    assert sensitive_message not in location, (
        f"Internal error message was leaked in redirect URL: {location}"
    )
    # Should contain a generic error message instead
    assert "error=" in location
    assert "An+internal+error+occurred." in location or "An internal error occurred." in location
