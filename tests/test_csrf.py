"""Tests for CSRF protection middleware (task 4.1)."""
import pytest
from fastapi import FastAPI, Form
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def csrf_app():
    from shared.csrf import CSRFMiddleware
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/form-submit")
    async def form_submit(name: str = Form(...)):
        return {"name": name}

    @app.post("/json-submit")
    async def json_submit():
        return {"ok": True}

    @app.get("/get-endpoint")
    async def get_endpoint():
        return {"ok": True}

    return app


async def test_form_post_same_origin_allowed(csrf_app):
    """Same-origin form POST passes CSRF check."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/form-submit",
            data={"name": "test"},
            headers={"origin": "http://testserver"},
        )
    assert resp.status_code == 200


async def test_form_post_cross_origin_rejected(csrf_app):
    """Cross-origin form POST is blocked with 403."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/form-submit",
            data={"name": "test"},
            headers={"origin": "http://evil.com"},
        )
    assert resp.status_code == 403


async def test_form_post_no_origin_no_referer_allowed(csrf_app):
    """Direct API call without Origin/Referer is allowed (curl, Postman, tests)."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post("/form-submit", data={"name": "test"})
    assert resp.status_code == 200


async def test_form_post_same_referer_allowed(csrf_app):
    """Form POST with a same-origin Referer passes CSRF check."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/form-submit",
            data={"name": "test"},
            headers={"referer": "http://testserver/login"},
        )
    assert resp.status_code == 200


async def test_form_post_cross_referer_rejected(csrf_app):
    """Form POST with a cross-origin Referer is blocked."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/form-submit",
            data={"name": "test"},
            headers={"referer": "http://evil.com/attack"},
        )
    assert resp.status_code == 403


async def test_null_origin_rejected(csrf_app):
    """'null' origin (sandboxed iframe) is blocked."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/form-submit",
            data={"name": "test"},
            headers={"origin": "null"},
        )
    assert resp.status_code == 403


async def test_json_post_cross_origin_not_checked(csrf_app):
    """JSON POST is not subject to CSRF check (stateless API)."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.post(
            "/json-submit",
            content=b"{}",
            headers={"content-type": "application/json", "origin": "http://evil.com"},
        )
    assert resp.status_code == 200


async def test_get_not_checked(csrf_app):
    """GET requests are never checked."""
    async with AsyncClient(transport=ASGITransport(app=csrf_app), base_url="http://testserver") as ac:
        resp = await ac.get("/get-endpoint", headers={"origin": "http://evil.com"})
    assert resp.status_code == 200
