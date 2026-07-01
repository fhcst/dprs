"""Tests for setup startup logic (lifespan checks)."""
import pytest
import fakeredis.aioredis as fakeredis
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def fake_redis():
    r = fakeredis.FakeRedis()
    yield r
    await r.aclose()


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_startup")
    from core.system.models import SystemConfig
    await init_beanie(database=database, document_models=[SystemConfig])
    yield database
    client.close()


async def test_redis_client_stored_in_app_state(fake_redis):
    """Redis client is injected into app.state.redis (async mode)."""
    from core.system.startup import init_redis_state

    class FakeState:
        pass

    state = FakeState()
    await init_redis_state(state, fake_redis)
    assert state.redis is fake_redis


async def test_setup_not_configured_sets_none(db, fake_redis):
    """When no flag and no config: app.state.system_config is None (Startup without completed setup)."""
    from core.system.startup import check_setup_state

    class FakeState:
        redis = fake_redis
        system_config = "sentinel"

    state = FakeState()
    await check_setup_state(state)
    assert state.system_config is None


async def test_setup_configured_loads_config(db, fake_redis):
    """When Redis flag is true: SystemConfig loaded into app.state (Startup with completed setup)."""
    from core.system.models import SystemConfig
    from core.system.startup import check_setup_state
    from shared.redis import SETUP_FLAG_KEY

    await SystemConfig(site_name="MySchool", admin_email="admin@school.com").insert()
    await fake_redis.set(SETUP_FLAG_KEY, "true")

    class FakeState:
        redis = fake_redis
        system_config = None

    state = FakeState()
    await check_setup_state(state)
    assert state.system_config is not None
    assert state.system_config.site_name == "MySchool"


async def test_redis_flag_missing_but_mongo_has_config(db, fake_redis):
    """When Redis flag absent but MongoDB has config: flag is restored (Redis flag missing but config exists)."""
    from core.system.models import SystemConfig
    from core.system.startup import check_setup_state
    from shared.redis import SETUP_FLAG_KEY

    await SystemConfig(site_name="Recovered", admin_email="r@r.com").insert()
    # Redis flag intentionally absent

    class FakeState:
        redis = fake_redis
        system_config = None

    state = FakeState()
    await check_setup_state(state)

    flag = await fake_redis.get(SETUP_FLAG_KEY)
    assert flag == b"true"
    assert state.system_config is not None
    assert state.system_config.site_name == "Recovered"


# ── JWT startup check (R2) ───────────────────────────────────────────────────

def test_check_secret_safety_raises_in_production_with_default_secret(monkeypatch):
    """check_secret_safety() must raise RuntimeError in production if SESSION_SECRET is default."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    monkeypatch.setenv("SESSION_SECRET", "dev-secret-change-in-production")
    import importlib
    import core.auth.jwt as jwt_mod
    importlib.reload(jwt_mod)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        jwt_mod.check_secret_safety()


def test_check_secret_safety_logs_warning_in_dev_with_default_secret(monkeypatch, caplog):
    """check_secret_safety() must only warn (not raise) in non-production with default secret."""
    import logging
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "development")
    monkeypatch.setenv("SESSION_SECRET", "dev-secret-change-in-production")
    import importlib
    import core.auth.jwt as jwt_mod
    importlib.reload(jwt_mod)
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        jwt_mod.check_secret_safety()  # must NOT raise
    assert any("SESSION_SECRET" in r.message for r in caplog.records)


def test_check_secret_safety_passes_with_custom_secret(monkeypatch):
    """check_secret_safety() must not raise or warn when SESSION_SECRET is set to a custom value."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-very-long-custom-production-secret-that-is-safe")
    import importlib
    import core.auth.jwt as jwt_mod
    importlib.reload(jwt_mod)
    jwt_mod.check_secret_safety()  # must not raise


# ── Rate limiting middleware (R4) ────────────────────────────────────────────

def test_slowapi_limiter_importable():
    """slowapi Limiter must be importable (dependency installed)."""
    from slowapi import Limiter
    assert Limiter is not None


def test_slowapi_limiter_attached_to_app():
    """app.state.limiter must be a SlowAPI Limiter instance."""
    from slowapi import Limiter
    import main as app_mod
    assert hasattr(app_mod.app.state, "limiter")
    assert isinstance(app_mod.app.state.limiter, Limiter)
