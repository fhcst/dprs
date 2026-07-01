"""Tests for user management CRUD, bulk, and import API endpoints (Tasks 5.2-5.4)."""
import csv
import io
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_admin_users")
    from core.users.models import User
    from core.system.models import SystemConfig
    await init_beanie(database=database, document_models=[User, SystemConfig])
    yield database
    client.close()


@pytest.fixture
def app():
    from fastapi import FastAPI
    from core.users.router import router
    app = FastAPI()
    app.include_router(router)
    return app


async def _make_user(permissions_val: int, username: str = "admin", db=None):
    from core.auth.password import hash_password
    from core.auth.jwt import create_access_token
    from core.users.models import User
    user = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name=username.capitalize(),
        permissions=permissions_val,
    )
    await user.insert()
    token = create_access_token(user_id=str(user.id), permissions=permissions_val)
    return user, token


# ── GET /admin/users ────────────────────────────────────────────────────────

async def test_user_list_returns_paginated_users(db, app):
    """GET /admin/users must return a list of users with pagination metadata."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)


async def test_user_list_requires_manage_users(db, app):
    """GET /admin/users must return 403 without MANAGE_USERS."""
    from core.auth.permissions import STUDENT
    _, token = await _make_user(int(STUDENT), username="student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users")
    assert resp.status_code == 403


async def test_user_list_includes_expected_fields(db, app):
    """User list entries must include id, username, display_name, permissions, tags."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users")
    assert resp.status_code == 200
    for user in resp.json()["users"]:
        assert "id" in user
        assert "username" in user
        assert "display_name" in user
        assert "permissions" in user
        assert "tags" in user


# ── GET /admin/users/{id} ────────────────────────────────────────────────────

async def test_single_user_read_returns_user(db, app):
    """GET /admin/users/{id} must return the user record."""
    from core.auth.permissions import SITE_ADMIN
    user, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get(f"/admin/users/{user.id}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


async def test_single_user_read_returns_404_for_missing(db, app):
    """GET /admin/users/{id} must return 404 for non-existent user."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/000000000000000000000000")
    assert resp.status_code == 404


# ── PUT /admin/users/{id} ────────────────────────────────────────────────────

async def test_user_update_changes_display_name(db, app):
    """PUT /admin/users/{id} must update display_name."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    user, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(f"/admin/users/{target.id}", json={"display_name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


async def test_user_update_does_not_change_password_when_absent(db, app):
    """PUT /admin/users/{id} without new_password must not change hashed_password."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User
    user, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    original_hash = target.hashed_password
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        await ac.put(f"/admin/users/{target.id}", json={"display_name": "X"})
    refreshed = await User.get(target.id)
    assert refreshed.hashed_password == original_hash


# ── DELETE /admin/users/{id} ─────────────────────────────────────────────────

async def test_user_delete_removes_user(db, app):
    """DELETE /admin/users/{id} must delete the user and return 204."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User
    user, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.delete(f"/admin/users/{target.id}")
    assert resp.status_code == 204
    assert await User.get(target.id) is None


async def test_user_delete_self_returns_400(db, app):
    """DELETE /admin/users/{id} with own id must return 400."""
    from core.auth.permissions import SITE_ADMIN
    user, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.delete(f"/admin/users/{user.id}")
    assert resp.status_code == 400


# ── DELETE /admin/users/bulk ─────────────────────────────────────────────────

async def test_bulk_delete_removes_multiple_users(db, app):
    """DELETE /admin/users/bulk must delete all specified users."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User
    admin, token = await _make_user(int(SITE_ADMIN))
    u1, _ = await _make_user(int(STUDENT), username="u1")
    u2, _ = await _make_user(int(STUDENT), username="u2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.request("DELETE", "/admin/users/bulk", json={"ids": [str(u1.id), str(u2.id)]})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2
    assert await User.get(u1.id) is None
    assert await User.get(u2.id) is None


async def test_bulk_delete_excludes_own_id(db, app):
    """DELETE /admin/users/bulk must silently exclude the caller's own ID."""
    from core.auth.permissions import SITE_ADMIN
    from core.users.models import User
    admin, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.request("DELETE", "/admin/users/bulk", json={"ids": [str(admin.id)]})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0
    assert await User.get(admin.id) is not None


# ── PATCH /admin/users/bulk ──────────────────────────────────────────────────

async def test_bulk_permissions_update(db, app):
    """PATCH /admin/users/bulk must update permissions for all specified users."""
    from core.auth.permissions import SITE_ADMIN, STUDENT, TEACHER
    from core.users.models import User
    admin, token = await _make_user(int(SITE_ADMIN))
    u1, _ = await _make_user(int(STUDENT), username="u1")
    u2, _ = await _make_user(int(STUDENT), username="u2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.patch("/admin/users/bulk", json={"ids": [str(u1.id), str(u2.id)], "permissions": int(TEACHER)})
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2
    r1 = await User.get(u1.id)
    assert r1.permissions == int(TEACHER)


# ── POST /admin/users/import ─────────────────────────────────────────────────

def _make_csv(*rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["username", "password", "display_name", "preset", "tags"])
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode()


async def test_csv_import_creates_valid_users(db, app):
    """POST /admin/users/import must create users from valid CSV rows."""
    from core.auth.permissions import SITE_ADMIN
    from core.users.models import User
    _, token = await _make_user(int(SITE_ADMIN))
    csv_data = _make_csv(
        ["alice", "password1", "Alice", "STUDENT", "math;science"],
        ["bob", "password2", "Bob", "TEACHER", ""],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 2
    assert data["failed"] == []
    assert await User.find_one(User.username == "alice") is not None


async def test_csv_import_skips_duplicate_username(db, app):
    """POST /admin/users/import must skip rows with existing usernames."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN), username="admin")
    csv_data = _make_csv(["admin", "password123", "Admin Again", "STUDENT", ""])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 0
    assert len(data["failed"]) == 1
    assert "already exists" in data["failed"][0]["reason"].lower()


async def test_csv_import_skips_invalid_preset(db, app):
    """POST /admin/users/import must skip rows with unknown preset names."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    csv_data = _make_csv(["newuser", "pw", "New User", "SUPERADMIN", ""])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 0
    assert len(data["failed"]) == 1
    assert "preset" in data["failed"][0]["reason"].lower()


# ── Password strength enforcement (R10) ─────────────────────────────────────

async def test_create_user_rejects_weak_password(db, app):
    """POST /admin/users must reject passwords shorter than 8 characters."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users", json={
            "username": "newu", "password": "short", "display_name": "New User",
        })
    assert resp.status_code == 422


async def test_update_user_rejects_weak_new_password(db, app):
    """PUT /admin/users/{id} must reject new_password shorter than 8 characters."""
    from core.auth.permissions import SITE_ADMIN
    user, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(f"/admin/users/{user.id}", json={"new_password": "weak"})
    assert resp.status_code == 422


async def test_csv_import_marks_weak_password_row_as_failed(db, app):
    """POST /admin/users/import must mark rows with weak passwords as failed."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    csv_data = _make_csv(["u1", "pw", "User One", "STUDENT", ""])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 0
    assert len(data["failed"]) == 1
    assert "密碼" in data["failed"][0]["reason"] or "password" in data["failed"][0]["reason"].lower()


# ── Permission ceiling checks (CWE-269) ─────────────────────────────────────

async def test_create_user_cannot_grant_higher_permissions(db, app):
    """POST /admin/users must return 403 when caller tries to set permissions
    higher than their own (e.g. USER_ADMIN granting WRITE_SYSTEM)."""
    from core.auth.permissions import USER_ADMIN, WRITE_SYSTEM
    _, token = await _make_user(int(USER_ADMIN), username="useradmin")
    # Try to create a user with WRITE_SYSTEM which USER_ADMIN doesn't have
    new_perms = int(USER_ADMIN | WRITE_SYSTEM)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users", json={
            "username": "newu",
            "password": "password123",
            "display_name": "New User",
            "permissions": new_perms,
        })
    assert resp.status_code == 403


async def test_create_user_can_grant_lower_or_equal_permissions(db, app):
    """POST /admin/users must return 201 when caller grants permissions
    that are a strict subset of their own (READ_USERS only for a USER_ADMIN caller)."""
    from core.auth.permissions import USER_ADMIN, READ_USERS
    _, token = await _make_user(int(USER_ADMIN), username="useradmin")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users", json={
            "username": "newstudent",
            "password": "password123",
            "display_name": "New Student",
            "permissions": int(READ_USERS),
        })
    assert resp.status_code == 201


async def test_update_user_cannot_grant_higher_permissions(db, app):
    """PUT /admin/users/{id} must return 403 when caller tries to set permissions
    higher than their own."""
    from core.auth.permissions import USER_ADMIN, STUDENT, WRITE_SYSTEM
    caller, token = await _make_user(int(USER_ADMIN), username="useradmin")
    target, _ = await _make_user(int(STUDENT), username="target")
    new_perms = int(USER_ADMIN | WRITE_SYSTEM)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(f"/admin/users/{target.id}", json={"permissions": new_perms})
    assert resp.status_code == 403


async def test_update_user_can_grant_lower_or_equal_permissions(db, app):
    """PUT /admin/users/{id} must return 200 when caller grants permissions
    that are a strict subset of their own."""
    from core.auth.permissions import USER_ADMIN, READ_USERS
    from core.auth.permissions import STUDENT
    caller, token = await _make_user(int(USER_ADMIN), username="useradmin")
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(f"/admin/users/{target.id}", json={"permissions": int(READ_USERS)})
    assert resp.status_code == 200


async def test_bulk_update_permissions_cannot_grant_higher(db, app):
    """PATCH /admin/users/bulk must return 403 when caller tries to set permissions
    higher than their own."""
    from core.auth.permissions import USER_ADMIN, STUDENT, WRITE_SYSTEM
    caller, token = await _make_user(int(USER_ADMIN), username="useradmin")
    target, _ = await _make_user(int(STUDENT), username="target")
    new_perms = int(USER_ADMIN | WRITE_SYSTEM)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.patch("/admin/users/bulk", json={
            "ids": [str(target.id)],
            "permissions": new_perms,
        })
    assert resp.status_code == 403


async def test_bulk_update_permissions_can_grant_lower_or_equal(db, app):
    """PATCH /admin/users/bulk must return 200 when caller grants permissions
    that are a strict subset of their own."""
    from core.auth.permissions import USER_ADMIN, READ_USERS
    from core.auth.permissions import STUDENT
    caller, token = await _make_user(int(USER_ADMIN), username="useradmin")
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.patch("/admin/users/bulk", json={
            "ids": [str(target.id)],
            "permissions": int(READ_USERS),
        })
    assert resp.status_code == 200


# ── File size limit (CWE-400) ────────────────────────────────────────────────

async def test_csv_import_rejects_file_over_1mb(db, app):
    """POST /admin/users/import must return 413 when the uploaded file exceeds 1 MB."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    # Generate a CSV payload that is just over 1 MB (1,048,576 bytes)
    oversized_data = b"x" * (1_048_576 + 1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post(
            "/admin/users/import",
            files={"file": ("big.csv", oversized_data, "text/csv")},
        )
    assert resp.status_code == 413


# ── GET /admin/users/check-username ────────────────────────────────────────

async def test_check_username_available(db, app):
    """GET /admin/users/check-username must return available=true for unused names."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/check-username", params={"username": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json()["available"] is True


async def test_check_username_taken(db, app):
    """GET /admin/users/check-username must return available=false for existing names."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN), username="admin")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/check-username", params={"username": "admin"})
    assert resp.status_code == 200
    assert resp.json()["available"] is False


async def test_check_username_requires_manage_users(db, app):
    """GET /admin/users/check-username must return 403 without MANAGE_USERS."""
    from core.auth.permissions import STUDENT
    _, token = await _make_user(int(STUDENT), username="student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/check-username", params={"username": "anyone"})
    assert resp.status_code == 403
