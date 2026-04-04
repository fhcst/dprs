"""Tests for task scheduling (TaskScheduleRule) and submission limits."""
import pytest
from datetime import date, timedelta
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_scheduling")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from tasks.templates.models import TaskTemplate, TaskAssignment, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
        ],
    )
    yield database
    client.close()


@pytest.fixture
async def teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(username="teach_sched", hashed_password=hash_password("pw"), display_name="T")
    await u.insert()
    return u


@pytest.fixture
async def template(db, teacher):
    from tasks.templates.service import create_template
    return await create_template(
        name="Test Template",
        description="",
        class_id="cls_sched",
        fields=[{"name": "note", "field_type": "text", "required": False}],
        owner=teacher,
    )


# ---------------------------------------------------------------------------
# Task 1.3: expand_schedule_rule tests
# ---------------------------------------------------------------------------

async def test_expand_schedule_rule_once_creates_one_assignment(db, template):
    """once mode creates exactly 1 TaskAssignment."""
    from tasks.templates.models import TaskScheduleRule
    from tasks.templates.service import expand_schedule_rule

    rule = TaskScheduleRule(
        template_id=str(template.id),
        class_id="cls_sched",
        schedule_type="once",
        date=date(2026, 4, 1),
        max_submissions_per_student=0,
    )
    await rule.insert()
    assignments = await expand_schedule_rule(rule)
    assert len(assignments) == 1
    assert assignments[0].date == date(2026, 4, 1)
    assert assignments[0].template_id == str(template.id)


async def test_expand_schedule_rule_range_with_weekdays_filters_correctly(db, template):
    """range + weekdays=[0,4] creates only Mon/Fri assignments."""
    from tasks.templates.models import TaskScheduleRule
    from tasks.templates.service import expand_schedule_rule

    # 2026-04-06=Mon, 2026-04-07=Tue, ..., 2026-04-10=Fri, ..., 2026-04-12=Sun
    rule = TaskScheduleRule(
        template_id=str(template.id),
        class_id="cls_sched",
        schedule_type="range",
        start_date=date(2026, 4, 6),   # Monday
        end_date=date(2026, 4, 12),    # Sunday
        weekdays=[0, 4],               # Mon=0, Fri=4
        max_submissions_per_student=0,
    )
    await rule.insert()
    assignments = await expand_schedule_rule(rule)
    assert len(assignments) == 2
    dates = {a.date for a in assignments}
    assert date(2026, 4, 6) in dates   # Monday
    assert date(2026, 4, 10) in dates  # Friday


async def test_expand_schedule_rule_open_expands_at_most_90_days(db, template):
    """open mode expands exactly 90 days starting from start_date."""
    from tasks.templates.models import TaskScheduleRule
    from tasks.templates.service import expand_schedule_rule

    rule = TaskScheduleRule(
        template_id=str(template.id),
        class_id="cls_sched",
        schedule_type="open",
        start_date=date(2026, 1, 1),
        max_submissions_per_student=0,
    )
    await rule.insert()
    assignments = await expand_schedule_rule(rule)
    assert len(assignments) == 90
    assert assignments[0].date == date(2026, 1, 1)
    assert assignments[-1].date == date(2026, 1, 1) + timedelta(days=89)


# ---------------------------------------------------------------------------
# Task 2.2: POST /classes/{class_id}/schedule-rules API tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def api_app(db):
    """FastAPI app with templates router for schedule-rule API tests."""
    from fastapi import FastAPI
    from tasks.templates.router import router as templates_router
    app = FastAPI()
    app.include_router(templates_router)
    return app


@pytest.fixture
async def api_teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    u = User(
        username="api_teacher",
        hashed_password=hash_password("pw"),
        display_name="API Teacher",
        permissions=int(TEACHER),
    )
    await u.insert()
    return u


@pytest.fixture
async def api_class(db, api_teacher):
    """A real Class document with valid ObjectId for API tests."""
    from core.classes.models import Class, ClassMembership
    cls = Class(
        name="API Test Class",
        description="",
        visibility="private",
        owner_id=str(api_teacher.id),
        invite_code="APITEST1",
    )
    await cls.insert()
    await ClassMembership(
        class_id=str(cls.id), user_id=str(api_teacher.id), role="teacher",
    ).insert()
    return cls


@pytest.fixture
async def api_template(db, api_teacher, api_class):
    """Template associated with a real Class (valid ObjectId)."""
    from tasks.templates.service import create_template
    return await create_template(
        name="API Test Template",
        description="",
        class_id=str(api_class.id),
        fields=[{"name": "note", "field_type": "text", "required": False}],
        owner=api_teacher,
    )


@pytest.fixture
async def api_client(db, api_app, api_teacher):
    from httpx import AsyncClient, ASGITransport
    from core.auth.jwt import create_access_token
    from core.auth.permissions import TEACHER
    token = create_access_token(user_id=str(api_teacher.id), permissions=int(TEACHER))
    cookies = {"access_token": token}
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://test", cookies=cookies
    ) as ac:
        yield ac


async def test_schedule_rule_range_returns_correct_count(db, api_client, api_class, api_template):
    """POST range rule with no weekday filter returns all days in range."""
    resp = await api_client.post(
        f"/classes/{api_class.id}/schedule-rules",
        json={
            "template_id": str(api_template.id),
            "schedule_type": "range",
            "start_date": "2026-04-01",
            "end_date": "2026-04-07",
            "weekdays": [],
            "max_submissions_per_student": 0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["assignments_created"] == 7


async def test_schedule_rule_weekday_filter_is_correct(db, api_client, api_class, api_template):
    """POST range rule with weekday filter [0,4] returns only Mon/Fri."""
    # 2026-04-06=Mon ... 2026-04-12=Sun → 2 assignments (Mon + Fri)
    resp = await api_client.post(
        f"/classes/{api_class.id}/schedule-rules",
        json={
            "template_id": str(api_template.id),
            "schedule_type": "range",
            "start_date": "2026-04-06",
            "end_date": "2026-04-12",
            "weekdays": [0, 4],
            "max_submissions_per_student": 0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["assignments_created"] == 2


async def test_schedule_rule_open_capped_at_90(db, api_client, api_class, api_template):
    """POST open rule creates at most 90 assignments."""
    resp = await api_client.post(
        f"/classes/{api_class.id}/schedule-rules",
        json={
            "template_id": str(api_template.id),
            "schedule_type": "open",
            "start_date": "2026-01-01",
            "max_submissions_per_student": 0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["assignments_created"] == 90


# ---------------------------------------------------------------------------
# Task 3.2: submit_task submission limit tests
# ---------------------------------------------------------------------------

async def test_submit_task_raises_when_limit_reached(db, template):
    """submit_task raises ValueError with 'limit' when max_submissions exceeded."""
    from tasks.templates.models import TaskScheduleRule
    from tasks.submissions.service import submit_task
    from core.users.models import User
    from core.auth.password import hash_password

    from core.classes.models import ClassMembership
    student = User(username="limit_stu", hashed_password=hash_password("pw"), display_name="S")
    await student.insert()
    await ClassMembership(class_id="cls_sched", user_id=str(student.id), role="student").insert()

    rule = TaskScheduleRule(
        template_id=str(template.id),
        class_id="cls_sched",
        schedule_type="range",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 5),
        weekdays=[],
        max_submissions_per_student=1,
    )
    await rule.insert()

    # First submission → OK
    await submit_task(template, "cls_sched", student, date(2026, 5, 1), {"note": "first"})

    # Second submission on different date → limit reached
    with pytest.raises(ValueError, match="limit"):
        await submit_task(template, "cls_sched", student, date(2026, 5, 2), {"note": "second"})


async def test_submit_task_no_limit_when_max_is_zero(db, template):
    """submit_task does not restrict when max_submissions_per_student is 0."""
    from tasks.templates.models import TaskScheduleRule
    from tasks.submissions.service import submit_task
    from core.users.models import User
    from core.auth.password import hash_password

    from core.classes.models import ClassMembership
    student = User(username="nolimit_stu", hashed_password=hash_password("pw"), display_name="S2")
    await student.insert()
    await ClassMembership(class_id="cls_sched", user_id=str(student.id), role="student").insert()

    rule = TaskScheduleRule(
        template_id=str(template.id),
        class_id="cls_sched",
        schedule_type="range",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        weekdays=[],
        max_submissions_per_student=0,
    )
    await rule.insert()

    # Multiple submissions should succeed
    await submit_task(template, "cls_sched", student, date(2026, 6, 1), {"note": "a"})
    await submit_task(template, "cls_sched", student, date(2026, 6, 2), {"note": "b"})
    await submit_task(template, "cls_sched", student, date(2026, 6, 3), {"note": "c"})


# ---------------------------------------------------------------------------
# Task 4.2: template_assign_page returns HTTP 200
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def register_auth_provider():
    from core.auth.local_provider import LocalAuthProvider
    from extensions.protocols import AuthProvider
    from extensions.registry import TestRegistry
    with TestRegistry() as reg:
        reg.register(AuthProvider, "local", LocalAuthProvider())
        yield


@pytest.fixture
async def page_app(db):
    from fastapi import FastAPI
    from core.auth.router import router as auth_router
    from gamification.badges.router import router as badges_router
    from pages.router import router as pages_router
    from tasks.submissions.router import router as submissions_router
    from tasks.templates.router import router as templates_router
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(badges_router)
    app.include_router(submissions_router)
    app.include_router(templates_router)
    return app


@pytest.fixture
async def page_teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    u = User(
        username="page_teacher",
        hashed_password=hash_password("pw"),
        display_name="Page Teacher",
        permissions=int(TEACHER),
    )
    await u.insert()
    return u


@pytest.fixture
async def page_template(db, page_teacher):
    """Template with a real class ObjectId (required by template_assign_page)."""
    from core.classes.models import Class
    from tasks.templates.service import create_template

    cls = Class(
        name="Page Class",
        description="",
        visibility="private",
        owner_id=str(page_teacher.id),
        invite_code="PAGE01",
    )
    await cls.insert()
    return await create_template(
        name="Page Template",
        description="",
        class_id=str(cls.id),
        fields=[{"name": "note", "field_type": "text", "required": False}],
        owner=page_teacher,
    )


async def test_template_assign_page_returns_200(db, page_app, page_teacher, page_template):
    """GET template assign page returns HTTP 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.jwt import create_access_token
    from core.auth.permissions import TEACHER

    token = create_access_token(user_id=str(page_teacher.id), permissions=int(TEACHER))
    cookies = {"access_token": token}
    async with AsyncClient(
        transport=ASGITransport(app=page_app), base_url="http://test", cookies=cookies
    ) as ac:
        response = await ac.get(
            f"/pages/teacher/templates/{page_template.id}/assign",
            follow_redirects=False,
        )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
