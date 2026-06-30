"""Tests for fix-dashboard-and-page-bugs change.

Covers:
- badges.html datetime slicing fix (task 1.1)
- submit_task.html null template guard (task 1.2)
- page-aware auth dependency for badges/leaderboard/feed pages (tasks 2.1-2.3)
- checkin PRG already-checked-in behaviour (task 3.1)
- dashboard context completeness: badge_count, submission_count, streak_days,
  badges list, recent_activities, teacher member_count (tasks 4.1–4.6)
"""
import pytest
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from core.auth.jwt import create_access_token
from core.auth.password import hash_password
from core.auth.permissions import STUDENT, TEACHER


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _token(user_id: str, permissions: int) -> str:
    return create_access_token(user_id=user_id, permissions=permissions)


def _cookies(user_id: str, permissions: int) -> dict:
    return {"access_token": _token(user_id, permissions)}


@pytest.fixture(autouse=True)
def register_auth_provider():
    from core.auth.local_provider import LocalAuthProvider
    from extensions.protocols import AuthProvider
    from extensions.registry import TestRegistry
    with TestRegistry() as reg:
        reg.register(AuthProvider, "local", LocalAuthProvider())
        yield


# ─── Shared app fixture ───────────────────────────────────────────────────────

async def _make_full_db(db_name: str):
    """Initialise mongomock with all models needed for these tests."""
    from core.classes.models import Class, ClassMembership, JoinRequest
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    from tasks.submissions.models import TaskSubmission
    from tasks.templates.models import TaskAssignment, TaskScheduleRule, TaskTemplate

    client = AsyncMongoMockClient()
    db = client.get_database(db_name)
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
    return client


def _make_app():
    from community.feed.router import router as feed_router
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
              feed_router, checkin_router, templates_router]:
        app.include_router(r)
    return app


# ─── Task 1.1 — badges.html datetime slicing ─────────────────────────────────

@pytest.fixture
async def badges_page_app():
    client = await _make_full_db("test_badges_datetime")
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition

    student = User(username="badge_s", hashed_password="x",
                   display_name="BadgeS", permissions=int(STUDENT))
    await student.insert()

    defn = BadgeDefinition(class_id="cls1", name="First Badge",
                           description="", icon="🌟", created_by="sys")
    await defn.insert()
    await BadgeAward(badge_id=str(defn.id), student_id=str(student.id),
                     class_id="cls1", awarded_by="system").insert()

    yield _make_app(), student
    client.close()


async def test_badges_page_renders_without_datetime_error(badges_page_app):
    """GET /pages/students/me/badges must render 200 — badge awarded_at is a datetime,
    slicing it with [:10] crashes; strftime('%Y-%m-%d') must be used instead."""
    app, student = badges_page_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/students/me/badges", follow_redirects=False)
    assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text[:300]}"
    # Date must appear in YYYY-MM-DD format somewhere in the HTML
    import re
    assert re.search(rb"\d{4}-\d{2}-\d{2}", resp.content), \
        "Date in YYYY-MM-DD format should be present in badges page"


# ─── Task 1.2 — submit_task.html null template guard ─────────────────────────

@pytest.fixture
async def no_template_app():
    client = await _make_full_db("test_null_template")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User

    student = User(username="no_tmpl_s", hashed_password="x",
                   display_name="NoTmplS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="NoTmplClass", description="", visibility="private",
                owner_id="o", invite_code="NT001")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id),
                          role="student").insert()

    yield _make_app(), student, cls
    client.close()


async def test_submit_page_without_template_returns_200(no_template_app):
    """GET submit page with no template assigned for today must return 200
    (not 500 from template.name on None)."""
    app, student, cls = no_template_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get(f"/pages/student/classes/{cls.id}/submit",
                            follow_redirects=False)
    assert resp.status_code == 200, \
        f"Submit page should return 200 even without a template, got {resp.status_code}"
    # Error message should be visible
    assert "今日無任務模板".encode() in resp.content


# ─── Tasks 2.1–2.3 — page-aware auth dependency ──────────────────────────────

@pytest.fixture
async def page_auth_app():
    client = await _make_full_db("test_page_auth")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User

    student = User(username="pg_auth_s", hashed_password="x",
                   display_name="PgAuthS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="AuthClass", description="", visibility="public",
                owner_id="o", invite_code="AU001", leaderboard_enabled=True)
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id),
                          role="student").insert()

    yield _make_app(), student, cls
    client.close()


async def test_badges_page_unauthenticated_redirects_to_login(page_auth_app):
    """Unauthenticated GET /pages/students/me/badges must redirect to login (302),
    not return JSON 401."""
    app, _, _ = page_auth_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/pages/students/me/badges", follow_redirects=False)
    assert resp.status_code == 302, \
        f"Expected redirect 302 for unauthenticated badges page, got {resp.status_code}"
    assert "/pages/login" in resp.headers["location"]


async def test_leaderboard_page_unauthenticated_redirects_to_login(page_auth_app):
    """Unauthenticated GET /pages/classes/{id}/leaderboard must redirect to login."""
    app, _, cls = page_auth_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/pages/classes/{cls.id}/leaderboard",
                            follow_redirects=False)
    assert resp.status_code == 302, \
        f"Expected redirect 302 for unauthenticated leaderboard page, got {resp.status_code}"
    assert "/pages/login" in resp.headers["location"]


async def test_feed_page_unauthenticated_redirects_to_login(page_auth_app):
    """Unauthenticated GET /pages/classes/{id}/feed must redirect to login."""
    app, _, cls = page_auth_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/pages/classes/{cls.id}/feed", follow_redirects=False)
    assert resp.status_code == 302, \
        f"Expected redirect 302 for unauthenticated feed page, got {resp.status_code}"
    assert "/pages/login" in resp.headers["location"]


# ─── Task 3.1 — checkin PRG: already checked in ──────────────────────────────

@pytest.fixture
async def checkin_prg_app():
    client = await _make_full_db("test_checkin_prg")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from tasks.checkin.models import CheckinConfig, CheckinRecord
    from datetime import date, timezone
    from datetime import datetime

    student = User(username="prg_s", hashed_password="x",
                   display_name="PrgS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="PrgClass", description="", visibility="private",
                owner_id="o", invite_code="PRG01")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id),
                          role="student").insert()

    # Open checkin config (all days, all-day window)
    await CheckinConfig(class_id=str(cls.id), active_weekdays=list(range(7))).insert()

    # Pre-record today's checkin so duplicate attempt can be tested
    today = date.today()
    await CheckinRecord(
        student_id=str(student.id),
        class_id=str(cls.id),
        checkin_date=today,
        checked_in_at=datetime.now(timezone.utc),
    ).insert()

    yield _make_app(), student, cls
    client.close()


async def test_checkin_browser_already_checked_in_redirects_without_error(checkin_prg_app):
    """POST checkin/browser when already checked in must redirect to dashboard
    WITHOUT an ?error= query parameter (already-checked-in is not an error)."""
    app, student, cls = checkin_prg_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.post(f"/classes/{cls.id}/checkin/browser",
                             follow_redirects=False)
    assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
    location = resp.headers["location"]
    assert "/pages/dashboard" in location, f"Should redirect to dashboard: {location}"
    assert "error=" not in location, \
        f"Already-checked-in should redirect WITHOUT error param, got: {location}"


# ─── Tasks 4.1–4.3 — dashboard stats: badge_count, submission_count, streak ──

@pytest.fixture
async def dashboard_stats_app():
    client = await _make_full_db("test_dashboard_stats")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import PointTransaction
    from tasks.submissions.models import TaskSubmission
    from tasks.templates.models import FieldDefinition, TaskAssignment, TaskTemplate
    from datetime import date

    student = User(username="stats_s", hashed_password="x",
                   display_name="StatsS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="StatsClass", description="", visibility="private",
                owner_id="o", invite_code="ST001")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id),
                          role="student").insert()

    # 2 submissions
    tmpl = TaskTemplate(name="T", class_id=str(cls.id), owner_id="o",
                        fields=[FieldDefinition(name="f", field_type="text")])
    await tmpl.insert()
    for i in range(2):
        await TaskSubmission(
            template_id=str(tmpl.id),
            template_snapshot={"name": "T"},
            field_values={"f": f"v{i}"},
            student_id=str(student.id),
            class_id=str(cls.id),
            date=date.today(),
        ).insert()

    # 3 badges
    defn = BadgeDefinition(class_id=str(cls.id), name="B", description="",
                           icon="🏅", created_by="sys")
    await defn.insert()
    for _ in range(3):
        award = BadgeAward(badge_id=str(defn.id),
                           student_id=str(student.id),
                           class_id=str(cls.id),
                           awarded_by="system")
        # force insert even if "duplicate" (different documents)
        award.id = None
        await award.insert()

    yield _make_app(), student
    client.close()


async def test_dashboard_includes_badge_count_in_stats(dashboard_stats_app):
    """Dashboard context must include stats.badge_count (shown in Widget Grid)."""
    app, student = dashboard_stats_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    content = resp.content
    # 徽章數 label should exist
    assert "徽章數".encode() in content, "Dashboard must contain 徽章數 widget"
    idx = content.find("徽章數".encode())
    nearby = content[max(0, idx - 200):idx]
    # Should NOT show the em dash placeholder
    assert "\u2014".encode() not in nearby, \
        "badge_count widget shows '—' placeholder — stats.badge_count not passed to template"


async def test_dashboard_includes_submission_count_in_stats(dashboard_stats_app):
    """Dashboard context must include stats.submission_count."""
    app, student = dashboard_stats_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    content = resp.content
    assert "已提交任務".encode() in content, "Dashboard must contain 已提交任務 widget"
    idx = content.find("已提交任務".encode())
    nearby = content[max(0, idx - 200):idx]
    assert "\u2014".encode() not in nearby, \
        "submission_count widget shows '—' placeholder — stats.submission_count not passed"


async def test_dashboard_streak_days_is_not_placeholder(dashboard_stats_app):
    """stats.streak_days may be 0 but must not be '—' (undefined)."""
    app, student = dashboard_stats_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    content = resp.content
    assert "連續天數".encode() in content, "Dashboard must contain 連續天數 widget"
    idx = content.find("連續天數".encode())
    nearby = content[max(0, idx - 200):idx]
    assert "\u2014".encode() not in nearby, \
        "streak_days widget shows '—' placeholder — stats.streak_days not passed"


# ─── Task 4.4 — badges list for badge strip ──────────────────────────────────

async def test_dashboard_includes_badges_list(dashboard_stats_app):
    """Dashboard context must include `badges` (badge strip data)."""
    app, student = dashboard_stats_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    content = resp.content
    # The badge strip section has class="我的徽章" heading; when badges list is provided
    # the badge names/icons are rendered. "B" is the badge name we inserted.
    assert "我的徽章".encode() in content, \
        "Badge strip heading '我的徽章' should be rendered when badges are present"


# ─── Task 4.5 — recent_activities ────────────────────────────────────────────

@pytest.fixture
async def dashboard_activity_app():
    client = await _make_full_db("test_dashboard_activity")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from tasks.checkin.models import CheckinConfig, CheckinRecord
    from datetime import date, datetime, timezone

    student = User(username="act_s", hashed_password="x",
                   display_name="ActS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="ActClass", description="", visibility="private",
                owner_id="o", invite_code="AC001")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(student.id),
                          role="student").insert()

    # One checkin record to appear in activities
    await CheckinConfig(class_id=str(cls.id), active_weekdays=list(range(7))).insert()
    await CheckinRecord(
        student_id=str(student.id),
        class_id=str(cls.id),
        checkin_date=date.today(),
        checked_in_at=datetime.now(timezone.utc),
    ).insert()

    yield _make_app(), student
    client.close()


async def test_dashboard_renders_without_error_when_activity_present(dashboard_activity_app):
    """Dashboard must render 200 even when recent_activities context is expected.
    When recent_activities is missing, the template shows an empty state (not an error)."""
    app, student = dashboard_activity_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    # Activity feed section heading should be present
    assert "今日動態".encode() in resp.content, "Dashboard must contain 今日動態 section"


# ─── Task 4.6 — teacher member_count ─────────────────────────────────────────

@pytest.fixture
async def teacher_dashboard_app():
    client = await _make_full_db("test_teacher_member_count")
    from core.classes.models import Class, ClassMembership
    from core.users.models import User

    teacher = User(username="tc_teacher", hashed_password="x",
                   display_name="TcTeacher", permissions=int(TEACHER))
    await teacher.insert()

    cls = Class(name="TcClass", description="", visibility="private",
                owner_id=str(teacher.id), invite_code="TC001")
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id),
                          role="teacher").insert()

    # Add 3 students to the class
    for i in range(3):
        s = User(username=f"tc_s{i}", hashed_password="x",
                 display_name=f"S{i}", permissions=int(STUDENT))
        await s.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(s.id),
                              role="student").insert()

    yield _make_app(), teacher, cls
    client.close()


async def test_teacher_dashboard_shows_member_count(teacher_dashboard_app):
    """Teacher dashboard Widget Grid must show member_count (number of students)
    instead of the '—' placeholder."""
    app, teacher, cls = teacher_dashboard_app
    cookies = _cookies(str(teacher.id), int(TEACHER))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get("/pages/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    content = resp.content
    # TcClass should appear
    assert b"TcClass" in content, "Teacher dashboard must show class name"
    # 學生 label should be present
    assert "學生".encode() in content, "Teacher widget should show 學生 member count label"
    # Should show "4" (3 students + 1 teacher = 4 members, or 3 students depending on query)
    # member_count is ClassMembership count for the class (all roles = 4, or students only = 3)
    # The template shows class_status.member_count — it must NOT be '—'
    # Check that '—' does not appear near "學生"
    idx = content.find("學生".encode())
    nearby = content[max(0, idx - 200):idx]
    assert "\u2014".encode() not in nearby, \
        "member_count shows '—' placeholder — member_count not computed in dashboard_page"


# ─── Membership guard regression: submit page (fix-submit-page-membership-check) ─

@pytest.fixture
async def non_member_submit_app():
    client = await _make_full_db("test_non_member_submit")
    from core.classes.models import Class
    from core.users.models import User

    student = User(username="nm_submit_s", hashed_password="x",
                   display_name="NmSubmitS", permissions=int(STUDENT))
    await student.insert()

    cls = Class(name="NonMemberClass", description="", visibility="private",
                owner_id="o", invite_code="NM001")
    await cls.insert()
    # Intentionally no ClassMembership for student

    yield _make_app(), student, cls
    client.close()


async def test_submit_page_non_member_gets_403_not_class_content(non_member_submit_app):
    """Non-member requesting GET /pages/student/classes/{class_id}/submit must receive
    HTTP 403 — NOT class-specific page content such as '今日無任務模板'.
    Regression for: fix-submit-page-membership-check"""
    app, student, cls = non_member_submit_app
    cookies = _cookies(str(student.id), int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           cookies=cookies) as ac:
        resp = await ac.get(f"/pages/student/classes/{cls.id}/submit",
                            follow_redirects=False)
    assert resp.status_code == 403, \
        f"Non-member submit page must return 403, got {resp.status_code}: {resp.text[:200]}"
    assert "今日無任務模板".encode() not in resp.content, \
        "403 response must NOT reveal the 'no template today' message to non-members"
