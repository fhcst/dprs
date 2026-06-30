"""Tests for teacher class hub page — route authorization and template rendering."""
import pytest
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from core.auth.jwt import create_access_token
from core.auth.password import hash_password
from core.auth.permissions import STUDENT, TEACHER


def _make_app():
    """Build a minimal FastAPI app with pages and required routers."""
    from core.auth.router import router as auth_router
    from gamification.badges.router import router as badges_router
    from gamification.leaderboard.router import router as leaderboard_router
    from gamification.points.router import router as points_router
    from pages.router import router as pages_router
    from tasks.checkin.router import router as checkin_router
    from tasks.submissions.router import router as submissions_router
    from tasks.templates.router import router as templates_router

    app = FastAPI()
    for r in [
        auth_router, pages_router, submissions_router,
        badges_router, leaderboard_router, points_router,
        checkin_router, templates_router,
    ]:
        app.include_router(r)
    return app


@pytest.fixture(autouse=True)
def register_auth_provider():
    from core.auth.local_provider import LocalAuthProvider
    from extensions.protocols import AuthProvider
    from extensions.registry import TestRegistry

    with TestRegistry() as reg:
        reg.register(AuthProvider, "local", LocalAuthProvider())
        yield


@pytest.fixture
async def db_app():
    from core.classes.models import Class, ClassMembership, JoinRequest
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    from tasks.templates.models import TaskAssignment, TaskScheduleRule, TaskTemplate
    from tasks.submissions.models import TaskSubmission

    client = AsyncMongoMockClient()
    db = client.get_database("test_class_hub")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership, JoinRequest,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
        ],
    )

    teacher = User(
        username="teacher1",
        hashed_password=hash_password("pass123"),
        display_name="Teacher One",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    student = User(
        username="student1",
        hashed_password=hash_password("pass123"),
        display_name="Student One",
        permissions=int(STUDENT),
    )
    await student.insert()

    cls = Class(
        name="Math Class",
        description="A math class",
        visibility="private",
        owner_id=str(teacher.id),
        invite_code="MATH01",
    )
    await cls.insert()

    # Teacher membership
    await ClassMembership(
        class_id=str(cls.id),
        user_id=str(teacher.id),
        role="teacher",
    ).insert()

    app = _make_app()
    yield app, teacher, student, cls

    client.close()


def _auth_cookie(user_id: str, permissions: int) -> dict:
    token = create_access_token(user_id=user_id, permissions=permissions)
    return {"access_token": token}


# ---------------------------------------------------------------------------
# Task 5.1: Class hub route permission tests
# ---------------------------------------------------------------------------

async def test_class_hub_authorized_teacher_returns_200(db_app):
    """Teacher with MANAGE_OWN_CLASS and membership can access hub page."""
    app, teacher, _, cls = db_app
    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/class/{cls.id}", follow_redirects=False)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_class_hub_shows_class_name(db_app):
    """Class hub page displays the class name."""
    app, teacher, _, cls = db_app
    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/class/{cls.id}", follow_redirects=False)
    assert response.status_code == 200
    assert "Math Class".encode() in response.content


async def test_class_hub_unauthorized_user_gets_403(db_app):
    """User without can_manage_class permission receives 403."""
    app, _, student, cls = db_app
    cookies = _auth_cookie(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/class/{cls.id}", follow_redirects=False)
    assert response.status_code == 403


async def test_class_hub_nonmember_teacher_gets_403(db_app):
    """Teacher without membership in the class cannot access hub (owns no class)."""
    from core.users.models import User

    app, _, _, cls = db_app

    other_teacher = User(
        username="other_teacher",
        hashed_password=hash_password("pass"),
        display_name="Other Teacher",
        permissions=int(TEACHER),
    )
    await other_teacher.insert()

    cookies = _auth_cookie(str(other_teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/class/{cls.id}", follow_redirects=False)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Task 5.2: Sidebar expansion logic — URL-based class detection
# ---------------------------------------------------------------------------

async def test_sidebar_shows_tool_links_when_on_class_hub_url(db_app):
    """When teacher is on the class hub URL, sidebar renders tool links for that class."""
    app, teacher, _, cls = db_app
    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get(f"/pages/teacher/class/{cls.id}", follow_redirects=False)
    assert response.status_code == 200
    content = response.content
    # Sidebar should show tool links when expanded
    assert "成員管理".encode() in content
    assert "任務模板".encode() in content
    assert "簽到設定".encode() in content
    assert "排行榜".encode() in content
    assert "積分管理".encode() in content


async def test_sidebar_does_not_expand_tool_links_on_dashboard(db_app):
    """When teacher is on dashboard, sidebar shows class names but not expanded tool links."""
    from core.classes.models import ClassMembership
    app, teacher, _, cls = db_app
    cookies = _auth_cookie(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies=cookies) as ac:
        response = await ac.get("/pages/dashboard", follow_redirects=False)
    assert response.status_code == 200
    content = response.content
    # Class name should appear as a hub link in sidebar
    assert "Math Class".encode() in content
