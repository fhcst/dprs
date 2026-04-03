"""Tests for pages router — login, dashboard, PRG patterns, and auth dependency."""
import pytest
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from core.auth.jwt import create_access_token
from core.auth.password import hash_password
from core.auth.permissions import STUDENT, TEACHER


def _make_app():
    """Build a minimal FastAPI app with all page-related routers."""
    from core.auth.router import router as auth_router
    from gamification.badges.router import router as badges_router
    from gamification.leaderboard.router import router as leaderboard_router
    from gamification.points.router import router as points_router
    from pages.router import router as pages_router
    from tasks.checkin.router import router as checkin_router
    from tasks.submissions.router import router as submissions_router
    from tasks.templates.router import router as templates_router

    app = FastAPI()
    for r in [auth_router, pages_router, submissions_router,
              badges_router, leaderboard_router, points_router,
              checkin_router, templates_router]:
        app.include_router(r)
    return app


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
async def db_app():
    """App with real MongoDB mock and pre-loaded users."""
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride, AttendanceCorrection
    from tasks.templates.models import TaskAssignment, TaskTemplate, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    from community.feed.models import FeedPost

    client = AsyncMongoMockClient()
    db = client.get_database("test_pages")
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

    # Seed a student and a teacher
    student = User(
        username="alice",
        hashed_password=hash_password("pass123"),
        display_name="Alice",
        permissions=int(STUDENT),
    )
    await student.insert()

    teacher = User(
        username="bob",
        hashed_password=hash_password("teachpass"),
        display_name="Bob",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    app = _make_app()
    yield app, student, teacher

    client.close()


def _auth_cookie(user_id: str, permissions: int) -> dict:
    token = create_access_token(user_id=user_id, permissions=permissions)
    return {"access_token": token}


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------

async def test_login_page_get_returns_html(db_app):
    """Login page GET renders HTML login form."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/pages/login", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<form" in response.content


async def test_login_page_shows_error_param(db_app):
    """Login page GET shows error message from query param."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/pages/login?error=帳號錯誤", follow_redirects=False)
    assert response.status_code == 200
    assert "帳號錯誤".encode() in response.content


# ---------------------------------------------------------------------------
# Form login PRG
# ---------------------------------------------------------------------------

async def test_form_login_success_redirects_to_dashboard(db_app):
    """Successful form login redirects to dashboard (PRG)."""
    app, student, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice", "password": "pass123"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert "/pages/dashboard" in response.headers["location"]
    # Cookie should be set
    assert "access_token" in response.cookies


async def test_form_login_failure_redirects_to_login_with_error(db_app):
    """Failed form login redirects back to login page with error query param."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice", "password": "wrong!"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    location = response.headers["location"]
    assert "/pages/login" in location
    assert "error=" in location


async def test_form_login_redirects_to_next_param(db_app):
    """Successful form login redirects to `next` if it is a safe relative URL."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice", "password": "pass123", "next": "/pages/dashboard"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert response.headers["location"] == "/pages/dashboard"


async def test_form_login_ignores_unsafe_next_param(db_app):
    """Unsafe `next` URL (external) is ignored — redirects to dashboard instead."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/pages/login",
            data={"username": "alice", "password": "pass123", "next": "https://evil.com"},
            follow_redirects=False,
        )
    assert response.status_code == 302
    assert "evil.com" not in response.headers["location"]
    assert "/pages/dashboard" in response.headers["location"]


# ---------------------------------------------------------------------------
# Logout redirect
# ---------------------------------------------------------------------------

async def test_logout_redirects_to_login(db_app):
    """Browser-based logout redirects to login page."""
    app, student, _ = db_app
    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/pages/login" in response.headers["location"]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def test_dashboard_requires_login(db_app):
    """Unauthenticated request to dashboard redirects to login."""
    app, _, _ = db_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert "/pages/login" in location
    assert "next=" in location


async def test_dashboard_renders_html_for_authenticated_student(db_app):
    """Authenticated student sees dashboard HTML."""
    app, student, _ = db_app
    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Student's name should appear
    assert b"Alice" in response.content


async def test_dashboard_renders_html_for_authenticated_teacher(db_app):
    """Authenticated teacher also sees dashboard HTML (no class memberships → empty list)."""
    app, _, teacher = db_app
    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"Bob" in response.content


# ---------------------------------------------------------------------------
# Dashboard context — student vs teacher (task 11.2)
# ---------------------------------------------------------------------------

async def test_dashboard_student_sees_class_data(db_app):
    """Dashboard for a student with a class membership shows class info."""
    from core.classes.models import Class, ClassMembership

    app, student, _ = db_app

    cls = Class(
        name="Test Class",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="ABC123",
    )
    await cls.insert()
    membership = ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student")
    await membership.insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)

    assert response.status_code == 200
    assert "Test Class".encode() in response.content


async def test_dashboard_teacher_sees_class_data(db_app):
    """Dashboard for a teacher with a class membership shows class info."""
    from core.classes.models import Class, ClassMembership

    app, _, teacher = db_app

    cls = Class(
        name="Teachers Class",
        description="",
        visibility="private",
        owner_id=str(teacher.id),
        invite_code="XYZ999",
    )
    await cls.insert()
    membership = ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher")
    await membership.insert()

    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)

    assert response.status_code == 200
    assert b"Teachers Class" in response.content


# ---------------------------------------------------------------------------
# Submit task page PRG (task 11.3)
# ---------------------------------------------------------------------------

async def test_submit_task_page_get_returns_html(db_app):
    """Student task submission GET page renders HTML."""
    from core.classes.models import Class, ClassMembership
    from tasks.templates.models import FieldDefinition, TaskAssignment, TaskTemplate
    from datetime import date

    app, student, _ = db_app

    cls = Class(
        name="Submit Class",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="SUB001",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student").insert()

    tmpl = TaskTemplate(
        name="Daily Log",
        class_id=str(cls.id),
        owner_id="owner",
        fields=[FieldDefinition(name="note", field_type="text", required=True)],
    )
    await tmpl.insert()
    await TaskAssignment(template_id=str(tmpl.id), class_id=str(cls.id), date=date.today()).insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(
            f"/pages/student/classes/{cls.id}/submit", follow_redirects=False
        )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_submit_task_form_success_shows_points(db_app):
    """Successful form submission PRG redirects to submit page with success and points params."""
    from core.classes.models import Class, ClassMembership
    from tasks.templates.models import FieldDefinition, TaskAssignment, TaskTemplate
    from gamification.points.models import ClassPointConfig, PointTransaction
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from datetime import date

    app, student, _ = db_app

    cls = Class(
        name="Submit Class 2",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="SUB002",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student").insert()

    tmpl = TaskTemplate(
        name="Daily Log 2",
        class_id=str(cls.id),
        owner_id="owner",
        fields=[FieldDefinition(name="note", field_type="text", required=False)],
    )
    await tmpl.insert()
    await TaskAssignment(template_id=str(tmpl.id), class_id=str(cls.id), date=date.today()).insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        # Register reward/badge models needed by the submission flow
        from beanie import init_beanie
        from mongomock_motor import AsyncMongoMockClient
        # (already initialised in fixture — just send the POST)
        response = await ac.post(
            f"/classes/{cls.id}/submit",
            data={"note": "my daily log"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert f"/pages/student/classes/{cls.id}/submit" in location
    assert "success=1" in location


async def test_submit_task_form_failure_redirects_with_error(db_app):
    """Form submission when no template assigned redirects back with error."""
    from core.classes.models import Class, ClassMembership

    app, student, _ = db_app

    cls = Class(
        name="No Template Class",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="NO001",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student").insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.post(
            f"/classes/{cls.id}/submit",
            data={"note": "test"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert f"/pages/student/classes/{cls.id}/submit" in location
    assert "error=" in location


# ---------------------------------------------------------------------------
# My Badges navigation link (task 1.4)
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_app_with_badges():
    """App with badges router included; needed to test badge navigation URL."""
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    from tasks.submissions.models import TaskSubmission
    from tasks.templates.models import TaskAssignment, TaskTemplate

    client = AsyncMongoMockClient()
    db = client.get_database("test_badges_nav")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskSubmission,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            BadgeDefinition, BadgeAward,
        ],
    )

    student = User(
        username="badge_alice",
        hashed_password="x",
        display_name="BadgeAlice",
        permissions=int(STUDENT),
    )
    await student.insert()

    from core.auth.router import router as auth_router
    from gamification.badges.router import router as badges_router
    from pages.router import router as pages_router
    from tasks.submissions.router import router as submissions_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(submissions_router)
    app.include_router(badges_router)
    yield app, student

    client.close()


async def test_my_badges_navigation_link_resolves_correctly(db_app_with_badges):
    """GET /pages/students/me/badges returns HTTP 200 for an authenticated student."""
    app, student = db_app_with_badges
    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/students/me/badges", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Access-control: rejection detail page (task 13.5)
# ---------------------------------------------------------------------------

async def test_rejection_detail_page_owner_can_access(db_app):
    """Owner can view their rejection detail page (Student views rejection detail page)."""
    from tasks.submissions.models import TaskSubmission
    app, student, teacher = db_app
    sub = TaskSubmission(
        template_id="t1",
        template_snapshot={"name": "Test"},
        field_values={"notes": "hi"},
        student_id=str(student.id),
        class_id="cls1",
        date=__import__("datetime").date.today(),
        status="rejected",
        rejection_reason="Bad",
    )
    await sub.insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/student/submissions/{sub.id}/rejection", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_rejection_detail_page_non_owner_forbidden(db_app):
    """Non-owner cannot access rejection detail (Non-owner cannot access rejection detail)."""
    from tasks.submissions.models import TaskSubmission
    app, student, teacher = db_app
    # Submission belongs to student; teacher tries to access it
    sub = TaskSubmission(
        template_id="t1",
        template_snapshot={"name": "Test"},
        field_values={"notes": "hi"},
        student_id=str(student.id),
        class_id="cls1",
        date=__import__("datetime").date.today(),
        status="rejected",
        rejection_reason="Bad",
    )
    await sub.insert()

    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/student/submissions/{sub.id}/rejection", follow_redirects=False)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Access-control: attendance management page (task 13.5)
# ---------------------------------------------------------------------------

async def test_attendance_manage_page_teacher_can_access(db_app):
    """Teacher can access attendance management page (Teacher views daily attendance list)."""
    from core.classes.models import Class, ClassMembership
    from gamification.points.models import ClassPointConfig
    app, student, teacher = db_app
    cls = Class(name="Math", visibility="public", owner_id=str(teacher.id), invite_code="XYZ")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()
    await ClassPointConfig(class_id=str(cls.id), checkin_points=5, submission_points=10).insert()

    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/classes/{cls.id}/attendance", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_attendance_manage_page_student_forbidden(db_app):
    """Student cannot access attendance management page (Teacher views daily attendance list)."""
    from core.classes.models import Class
    app, student, teacher = db_app
    cls = Class(name="Math", visibility="public", owner_id=str(teacher.id), invite_code="XYZ")
    await cls.insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/classes/{cls.id}/attendance", follow_redirects=False)
    assert response.status_code in (403, 401)


# ---------------------------------------------------------------------------
# Submit task page membership guard (fix-submit-page-membership-check)
# ---------------------------------------------------------------------------

async def test_submit_task_page_member_can_access(db_app):
    """Class member can open the student submit page (Class member can open the submit page)."""
    from core.classes.models import Class, ClassMembership

    app, student, _ = db_app

    cls = Class(
        name="Member Guard Class",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="MBR001",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student").insert()

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(
            f"/pages/student/classes/{cls.id}/submit", follow_redirects=False
        )

    assert response.status_code == 200


async def test_submit_task_page_non_member_gets_403(db_app):
    """Non-member is rejected before class task details are revealed (HTTP 403)."""
    from core.classes.models import Class

    app, student, _ = db_app

    cls = Class(
        name="Non Member Guard Class",
        description="",
        visibility="private",
        owner_id="owner",
        invite_code="NMB001",
    )
    await cls.insert()
    # Intentionally no ClassMembership for student

    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(
            f"/pages/student/classes/{cls.id}/submit", follow_redirects=False
        )

    assert response.status_code == 403
