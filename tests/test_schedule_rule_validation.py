"""Malformed schedule rules must be rejected before persistence (FINDING-004, CWE-20).

Previously ScheduleRuleRequest accepted an unbounded schedule_type and optional
date fields, so a rule missing its required dates was persisted and then crashed
expand_schedule_rule(). The request model now validates mode-specific fields and
rejects malformed input with 422 before any DB write.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


@pytest.fixture
async def schedule_app():
    """Teacher manages class Alpha, which has one template."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    from tasks.templates.models import TaskTemplate, TaskScheduleRule, TaskAssignment

    client = AsyncMongoMockClient()
    db = client.get_database("test_schedule_rule_validation")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskScheduleRule, TaskAssignment,
        ],
    )

    teacher = User(
        username="teacher_s",
        hashed_password=hash_password("pw"),
        display_name="Teacher S",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    alpha = Class(
        name="Alpha",
        visibility="private",
        owner_id=str(teacher.id),
        invite_code="ALPHA001",
    )
    await alpha.insert()
    await ClassMembership(
        class_id=str(alpha.id), user_id=str(teacher.id), role="teacher",
    ).insert()

    tmpl = TaskTemplate(
        name="Daily",
        description="",
        class_id=str(alpha.id),
        owner_id=str(teacher.id),
        fields=[],
    )
    await tmpl.insert()

    from fastapi import FastAPI
    from tasks.templates.router import router as templates_router

    app = FastAPI()
    app.include_router(templates_router)

    yield app, teacher, alpha, tmpl
    client.close()


async def _post_rule(app, teacher, alpha, body):
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        return await ac.post(f"/classes/{alpha.id}/schedule-rules", json=body)


async def test_once_without_date_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "once",
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_range_without_end_date_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "range",
        "start_date": "2026-03-01",
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_range_end_before_start_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "range",
        "start_date": "2026-03-10", "end_date": "2026-03-01",
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_open_without_start_date_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "open",
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_out_of_range_weekday_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "range",
        "start_date": "2026-03-01", "end_date": "2026-03-31", "weekdays": [7],
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_invalid_schedule_type_is_rejected(schedule_app):
    from tasks.templates.models import TaskScheduleRule
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "forever",
    })
    assert resp.status_code == 422
    assert await TaskScheduleRule.count() == 0


async def test_valid_once_rule_is_created(schedule_app):
    from tasks.templates.models import TaskScheduleRule, TaskAssignment
    app, teacher, alpha, tmpl = schedule_app
    resp = await _post_rule(app, teacher, alpha, {
        "template_id": str(tmpl.id), "schedule_type": "once",
        "date": "2026-03-15",
    })
    assert resp.status_code == 201
    assert await TaskScheduleRule.count() == 1
    assert await TaskAssignment.count() == 1
