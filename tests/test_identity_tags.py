"""Tests for identity tags, user profile visibility, self-edit, and CSV templates."""
import csv
import io
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_identity_tags")
    from core.users.models import User
    from core.system.models import SystemConfig
    await init_beanie(database=database, document_models=[User, SystemConfig])
    yield database
    client.close()


@pytest.fixture
def admin_app():
    from fastapi import FastAPI
    from core.users.router import router
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def auth_app():
    from fastapi import FastAPI
    from core.auth.router import router
    app = FastAPI()
    app.include_router(router)
    return app


async def _make_user(permissions_val: int, username: str = "admin",
                     identity_tags=None, name: str = "", email: str = "",
                     student_profile=None):
    from core.auth.password import hash_password
    from core.auth.jwt import create_access_token
    from core.users.models import User
    user = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name=username.capitalize(),
        permissions=permissions_val,
        name=name,
        email=email,
        identity_tags=identity_tags or [],
        student_profile=student_profile,
    )
    await user.insert()
    token = create_access_token(user_id=str(user.id), permissions=permissions_val)
    return user, token


# ── GET /admin/permissions/identity-tags ─────────────────────────────────────

async def test_identity_tags_endpoint_returns_all_values(db, admin_app):
    """GET /admin/permissions/identity-tags must return teacher, student, staff."""
    from core.auth.permissions import MANAGE_USERS, READ_OWN_PROFILE, WRITE_OWN_PROFILE
    _, token = await _make_user(int(MANAGE_USERS | READ_OWN_PROFILE | WRITE_OWN_PROFILE))
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/permissions/identity-tags")
    assert resp.status_code == 200
    values = resp.json()
    assert "teacher" in values
    assert "student" in values
    assert "staff" in values


async def test_identity_tags_endpoint_requires_manage_users(db, admin_app):
    """GET /admin/permissions/identity-tags must require MANAGE_USERS."""
    from core.auth.permissions import STUDENT
    _, token = await _make_user(int(STUDENT), username="stu")
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/permissions/identity-tags")
    assert resp.status_code == 403


# ── PUT /admin/users/{id} — identity_tags update ─────────────────────────────

async def test_admin_can_set_identity_tags(db, admin_app):
    """PUT /admin/users/{id} must allow MANAGE_USERS to update identity_tags."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User, IdentityTag
    admin, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(
            f"/admin/users/{target.id}",
            json={"identity_tags": ["student"]},
        )
    assert resp.status_code == 200
    refreshed = await User.get(target.id)
    assert IdentityTag.STUDENT in refreshed.identity_tags


async def test_admin_can_set_name_and_email(db, admin_app):
    """PUT /admin/users/{id} must allow MANAGE_USERS to update name and email."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User
    admin, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(
            f"/admin/users/{target.id}",
            json={"name": "陳小明", "email": "chen@school.edu"},
        )
    assert resp.status_code == 200
    refreshed = await User.get(target.id)
    assert refreshed.name == "陳小明"
    assert refreshed.email == "chen@school.edu"


async def test_admin_can_set_student_profile(db, admin_app):
    """PUT /admin/users/{id} must allow MANAGE_USERS to update student_profile."""
    from core.auth.permissions import SITE_ADMIN, STUDENT
    from core.users.models import User
    admin, token = await _make_user(int(SITE_ADMIN))
    target, _ = await _make_user(int(STUDENT), username="target")
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put(
            f"/admin/users/{target.id}",
            json={"student_profile": {"class_name": "302班", "seat_number": 5}},
        )
    assert resp.status_code == 200
    refreshed = await User.get(target.id)
    assert refreshed.student_profile.class_name == "302班"
    assert refreshed.student_profile.seat_number == 5


# ── User list / get returns new fields ───────────────────────────────────────

async def test_user_list_includes_new_fields(db, admin_app):
    """GET /admin/users must include name, email, identity_tags, student_profile."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN), name="Admin", email="a@b.com")
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users")
    assert resp.status_code == 200
    user_data = resp.json()["users"][0]
    assert "name" in user_data
    assert "email" in user_data
    assert "identity_tags" in user_data
    assert "student_profile" in user_data


async def test_single_user_read_includes_new_fields(db, admin_app):
    """GET /admin/users/{id} must include name, email, identity_tags, student_profile."""
    from core.auth.permissions import SITE_ADMIN
    from core.users.models import IdentityTag, StudentProfile
    user, token = await _make_user(
        int(SITE_ADMIN),
        name="Admin Real",
        email="ar@b.com",
        identity_tags=[IdentityTag.TEACHER],
        student_profile=None,
    )
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get(f"/admin/users/{user.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Admin Real"
    assert data["email"] == "ar@b.com"
    assert "teacher" in data["identity_tags"]


# ── PUT /auth/profile — self-edit ────────────────────────────────────────────

async def test_self_profile_update_changes_display_name(db, auth_app):
    """PUT /auth/profile must update only display_name."""
    from core.auth.permissions import STUDENT
    from core.users.models import User
    user, token = await _make_user(int(STUDENT), username="stu", name="Real Name")
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.put("/auth/profile", json={"display_name": "New Nick"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Nick"
    refreshed = await User.get(user.id)
    assert refreshed.display_name == "New Nick"


async def test_self_profile_update_ignores_name_field(db, auth_app):
    """PUT /auth/profile must ignore name field — it stays unchanged."""
    from core.auth.permissions import STUDENT
    from core.users.models import User
    user, token = await _make_user(int(STUDENT), username="stu", name="Real Name")
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        await ac.put("/auth/profile", json={"display_name": "Nick", "name": "HACKED"})
    refreshed = await User.get(user.id)
    assert refreshed.name == "Real Name"  # unchanged


async def test_self_profile_requires_auth(db, auth_app):
    """PUT /auth/profile without auth must return 401."""
    async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as ac:
        resp = await ac.put("/auth/profile", json={"display_name": "X"})
    assert resp.status_code == 401


# ── CSV import with new fields ────────────────────────────────────────────────

def _make_new_csv(*rows, extra_headers=None):
    """Build CSV with new extended headers."""
    headers = ["username", "password", "display_name", "name", "email",
               "identity_tag", "preset", "tags", "class_name", "seat_number"]
    if extra_headers:
        headers += extra_headers
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode()


async def test_csv_import_new_format_creates_user_with_identity_tag(db, admin_app):
    """CSV import with identity_tag column must populate identity_tags."""
    from core.auth.permissions import SITE_ADMIN
    from core.users.models import User, IdentityTag
    _, token = await _make_user(int(SITE_ADMIN))
    csv_data = _make_new_csv(
        ["stu1", "password123", "Stu1", "陳小明", "stu@school.edu", "student", "STUDENT", "", "302班", "5"]
    )
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    assert resp.json()["success"] == 1
    u = await User.find_one(User.username == "stu1")
    assert IdentityTag.STUDENT in u.identity_tags
    assert u.name == "陳小明"
    assert u.student_profile.class_name == "302班"
    assert u.student_profile.seat_number == 5


async def test_csv_import_skips_invalid_identity_tag(db, admin_app):
    """CSV import with unknown identity_tag must skip and report."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    csv_data = _make_new_csv(
        ["u2", "password123", "U2", "Name", "e@e.com", "robot", "STUDENT", "", "", ""]
    )
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.post("/admin/users/import", files={"file": ("users.csv", csv_data, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 0
    assert len(data["failed"]) == 1
    assert "identity tag" in data["failed"][0]["reason"].lower()


# ── GET /admin/users/import/template ─────────────────────────────────────────

async def test_student_template_download(db, admin_app):
    """GET /admin/users/import/template?type=student must return a CSV file."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/import/template?type=student")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")
    # Must have student-specific columns
    content = resp.text
    assert "class_name" in content
    assert "seat_number" in content
    assert "identity_tag" in content


async def test_staff_template_download(db, admin_app):
    """GET /admin/users/import/template?type=staff must return a CSV file."""
    from core.auth.permissions import SITE_ADMIN
    _, token = await _make_user(int(SITE_ADMIN))
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/admin/users/import/template?type=staff")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    content = resp.text
    assert "identity_tag" in content
    # Must NOT include student-specific fields
    assert "class_name" not in content
