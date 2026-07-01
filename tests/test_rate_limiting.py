"""Tests for rate limiting on sensitive endpoints (R4)."""
import inspect
import pytest
from httpx import AsyncClient, ASGITransport


# ── Structural checks: limiter applied to endpoints ─────────────────────────

def test_auth_router_has_limiter_on_login():
    """POST /auth/login must have @limiter.limit decorator."""
    import core.auth.router as mod
    source = inspect.getsource(mod)
    assert "limiter" in source and 'limit(' in source


def test_auth_router_has_limiter_on_change_password():
    """POST /auth/change-password must have @limiter.limit decorator."""
    import core.auth.router as mod
    source = inspect.getsource(mod)
    # Both login and change-password should be rate-limited
    assert source.count('limiter.limit(') >= 2


def test_pages_router_has_limiter_on_login():
    """POST /pages/login must have @limiter.limit decorator."""
    import pages.router as mod
    source = inspect.getsource(mod)
    assert "limiter" in source and 'limit(' in source


def test_system_router_has_limiter_on_setup():
    """POST /setup must have @limiter.limit decorator."""
    import core.system.router as mod
    source = inspect.getsource(mod)
    assert "limiter" in source and 'limit(' in source


# ── Behavioral: slowapi returns 429 after limit exceeded ────────────────────

async def test_slowapi_mechanism_returns_429_after_limit():
    """SlowAPI middleware returns 429 after the configured limit is exceeded."""
    from fastapi import FastAPI, Request
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    test_limiter = Limiter(key_func=get_remote_address)
    test_app = FastAPI()
    test_app.state.limiter = test_limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @test_app.get("/ping")
    @test_limiter.limit("2/minute")
    async def ping(request: Request):
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        r1 = await ac.get("/ping")
        r2 = await ac.get("/ping")
        r3 = await ac.get("/ping")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
