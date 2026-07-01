"""Tests that cross-class submission approve/reject/comment are rejected."""
import pytest
from datetime import date, datetime, timezone
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def cross_class_app():
    """Two teachers (A manages Alpha, B manages Beta).

    A pending TaskSubmission exists in class Alpha.
    """
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    from tasks.submissions.models import TaskSubmission
    from gamification.points.models import PointTransaction, ClassPointConfig
    from community.feed.models import FeedPost, Reaction

    client = AsyncMongoMockClient()
    db = client.get_database("test_cross_class_submissions")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            TaskSubmission,
            PointTransaction, ClassPointConfig,
            FeedPost, Reaction,
        ],
    )

    # Create teachers
    teacher_a = User(
        username="teacher_a",
        hashed_password=hash_password("pw"),
        display_name="Teacher A",
        permissions=int(TEACHER),
    )
    await teacher_a.insert()

    teacher_b = User(
        username="teacher_b",
        hashed_password=hash_password("pw"),
        display_name="Teacher B",
        permissions=int(TEACHER),
    )
    await teacher_b.insert()

    # Create classes
    cls_alpha = Class(
        name="Alpha",
        visibility="private",
        owner_id=str(teacher_a.id),
        invite_code="ALPHA001",
    )
    await cls_alpha.insert()

    cls_beta = Class(
        name="Beta",
        visibility="private",
        owner_id=str(teacher_b.id),
        invite_code="BETA0001",
    )
    await cls_beta.insert()

    # Create memberships — each teacher is a member of their own class only
    await ClassMembership(
        class_id=str(cls_alpha.id), user_id=str(teacher_a.id), role="teacher"
    ).insert()
    await ClassMembership(
        class_id=str(cls_beta.id), user_id=str(teacher_b.id), role="teacher"
    ).insert()

    # Create a point config for Alpha so approve/reject don't error
    await ClassPointConfig(
        class_id=str(cls_alpha.id), checkin_points=5, submission_points=10
    ).insert()

    # Create a pending submission in class Alpha
    submission = TaskSubmission(
        template_id="tmpl1",
        class_id=str(cls_alpha.id),
        student_id="student1",
        date=date(2026, 3, 24),
        field_values={"notes": "hello"},
        template_snapshot={
            "id": "tmpl1", "name": "Daily", "description": "", "fields": []
        },
        status="pending",
        submitted_at=datetime.now(timezone.utc),
    )
    await submission.insert()

    # Build a minimal FastAPI app with the submissions router
    from fastapi import FastAPI
    from tasks.submissions.router import router as submissions_router

    app = FastAPI()
    app.include_router(submissions_router)

    yield app, teacher_a, teacher_b, cls_alpha, cls_beta, submission
    client.close()


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


async def test_teacher_cannot_approve_submission_in_another_class(cross_class_app):
    """Teacher B tries to approve a submission in Alpha (not their class) — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_b.id), int(TEACHER)))
        resp = await ac.post(f"/api/submissions/{submission.id}/approve")
    assert resp.status_code == 403


async def test_teacher_cannot_reject_submission_in_another_class(cross_class_app):
    """Teacher B tries to reject a submission in Alpha (not their class) — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_b.id), int(TEACHER)))
        resp = await ac.post(
            f"/api/submissions/{submission.id}/reject",
            json={"rejection_reason": "test"},
        )
    assert resp.status_code == 403


async def test_teacher_cannot_comment_submission_in_another_class(cross_class_app):
    """Teacher B tries to comment on a submission in Alpha (not their class) — 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_b.id), int(TEACHER)))
        resp = await ac.post(
            f"/api/submissions/{submission.id}/comment",
            json={"comment": "test"},
        )
    assert resp.status_code == 403


async def test_owner_teacher_can_approve_own_class_submission(cross_class_app):
    """Teacher A approves a submission in Alpha (their own class) — 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_a.id), int(TEACHER)))
        resp = await ac.post(f"/api/submissions/{submission.id}/approve")
    assert resp.status_code == 200


async def test_teacher_cannot_read_class_submissions_in_another_class(cross_class_app):
    """Teacher B lists Alpha's submissions (not their class) — 403 (FINDING-001)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_b.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls_alpha.id}/submissions")
    assert resp.status_code == 403


async def test_owner_teacher_can_read_own_class_submissions(cross_class_app):
    """Teacher A lists Alpha's submissions (their own class) — 200 (FINDING-001)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher_a, teacher_b, cls_alpha, cls_beta, submission = cross_class_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.cookies.set("access_token", _token(str(teacher_a.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls_alpha.id}/submissions")
    assert resp.status_code == 200
