"""Cross-class authorization on teacher page/read routes (FINDING-001, CWE-639).

A teacher who manages class Beta must not be able to read class Alpha's
submission review, attendance, template, or points-management pages by
supplying Alpha's id. Each route must enforce can_manage_class on the target
class, not merely the MANAGE_TASKS permission flag. The 403 guard fires before
any template rendering, so these assert the security boundary directly.
"""
import pytest
from datetime import date, datetime, timezone
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


@pytest.fixture
async def two_class_app():
    """Teacher A manages Alpha (with a template + submission); Teacher B manages Beta."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    from tasks.submissions.models import TaskSubmission
    from tasks.templates.models import TaskTemplate

    client = AsyncMongoMockClient()
    db = client.get_database("test_cross_class_page_authz")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership, TaskSubmission, TaskTemplate,
        ],
    )

    teacher_a = User(username="tA", hashed_password=hash_password("pw"),
                     display_name="A", permissions=int(TEACHER))
    await teacher_a.insert()
    teacher_b = User(username="tB", hashed_password=hash_password("pw"),
                     display_name="B", permissions=int(TEACHER))
    await teacher_b.insert()

    alpha = Class(name="Alpha", visibility="private",
                  owner_id=str(teacher_a.id), invite_code="ALPHA001")
    await alpha.insert()
    beta = Class(name="Beta", visibility="private",
                 owner_id=str(teacher_b.id), invite_code="BETA0001")
    await beta.insert()
    await ClassMembership(class_id=str(alpha.id), user_id=str(teacher_a.id), role="teacher").insert()
    await ClassMembership(class_id=str(beta.id), user_id=str(teacher_b.id), role="teacher").insert()

    tmpl = TaskTemplate(name="Daily", description="", class_id=str(alpha.id),
                        owner_id=str(teacher_a.id), fields=[])
    await tmpl.insert()

    await TaskSubmission(
        template_id=str(tmpl.id), class_id=str(alpha.id), student_id="s1",
        date=date(2026, 3, 24), field_values={}, template_snapshot={},
        status="pending", submitted_at=datetime.now(timezone.utc),
    ).insert()

    from fastapi import FastAPI
    from tasks.submissions.router import router as submissions_router
    from tasks.checkin.router import router as checkin_router
    from tasks.templates.router import router as templates_router
    from gamification.points.router import router as points_router

    app = FastAPI()
    for r in (submissions_router, checkin_router, templates_router, points_router):
        app.include_router(r)

    yield app, teacher_b, alpha, tmpl
    client.close()


async def _get_as_b(app, teacher_b, url):
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher_b.id), int(TEACHER)))
        return await ac.get(url)


async def test_submission_review_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/teacher/class/{alpha.id}/submissions")
    assert resp.status_code == 403


async def test_attendance_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/teacher/classes/{alpha.id}/attendance")
    assert resp.status_code == 403


async def test_templates_list_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/teacher/classes/{alpha.id}/templates")
    assert resp.status_code == 403


async def test_template_edit_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/teacher/templates/{tmpl.id}/edit")
    assert resp.status_code == 403


async def test_template_assign_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/teacher/templates/{tmpl.id}/assign")
    assert resp.status_code == 403


async def test_points_manage_page_cross_class_forbidden(two_class_app):
    app, teacher_b, alpha, tmpl = two_class_app
    resp = await _get_as_b(app, teacher_b, f"/pages/classes/{alpha.id}/points")
    assert resp.status_code == 403
