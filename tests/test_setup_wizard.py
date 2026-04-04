"""Tests for the setup wizard router."""
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
import fakeredis.aioredis as fakeredis


@pytest.fixture
async def setup_app():
    """A minimal FastAPI app wired with test DB + fake Redis for setup wizard tests."""
    from core.system.router import router as system_router
    from core.users.models import User
    from core.system.models import SystemConfig
    from shared.limiter import limiter

    client = AsyncMongoMockClient()
    db = client.get_database("test_setup_wizard")
    await init_beanie(database=db, document_models=[User, SystemConfig])

    r = fakeredis.FakeRedis()

    app = FastAPI()
    app.state.redis = r
    app.state.system_config = None  # not configured yet

    from pages.router import router as pages_router
    app.include_router(pages_router)
    app.include_router(system_router)

    # Disable rate limiter in tests to prevent cross-test state leakage
    limiter.enabled = False
    yield app, r
    limiter.enabled = True

    await r.aclose()
    client.close()


async def test_get_setup_returns_html_when_not_configured(setup_app):
    """Setup wizard is shown on first deployment when not configured."""
    app, _ = setup_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/setup", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_get_setup_redirects_when_configured(setup_app):
    """Setup page blocked after configuration — redirects to /."""
    from shared.redis import SETUP_FLAG_KEY
    app, r = setup_app
    await r.set(SETUP_FLAG_KEY, "true")
    app.state.system_config = object()  # non-None signals configured

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/setup", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


async def test_post_setup_creates_config_and_redirects(setup_app):
    """Successful setup submission creates SystemConfig, User, sets Redis flag."""
    from core.system.models import SystemConfig
    from core.users.models import User
    from shared.redis import SETUP_FLAG_KEY

    app, r = setup_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/setup",
            data={
                "site_name": "Test School",
                "admin_username": "admin",
                "admin_password": "SuperSecret1!",
            },
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert response.headers["location"] == "/"

    config = await SystemConfig.find_one()
    assert config is not None
    assert config.site_name == "Test School"

    admin = await User.find_one(User.username == "admin")
    assert admin is not None

    flag = await r.get(SETUP_FLAG_KEY)
    assert flag == b"true"


async def test_post_setup_returns_409_when_already_configured(setup_app):
    """Duplicate setup attempt via API returns 409 Conflict."""
    from shared.redis import SETUP_FLAG_KEY
    app, r = setup_app
    await r.set(SETUP_FLAG_KEY, "true")
    app.state.system_config = object()  # configured

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/setup",
            data={
                "site_name": "Again",
                "admin_username": "admin2",
                "admin_password": "password",
            },
            follow_redirects=False,
        )
    assert response.status_code == 409
