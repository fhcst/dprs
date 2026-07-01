"""Tests for cross-class gamification isolation.

Verify that a teacher cannot manipulate points, badges, or prizes in a class
they do not own, while the owning teacher can operate normally.

Setup: Teacher A manages class Alpha, Teacher B manages class Beta.
A student belongs to class Alpha.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


@pytest.fixture
async def cross_class_app():
    """Two teachers (A→Alpha, B→Beta), one student in Alpha."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT
    from gamification.points.models import PointTransaction, ClassPointConfig
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.prizes.models import Prize

    client = AsyncMongoMockClient()
    db = client.get_database("test_cross_class_gamification")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
            Prize,
        ],
    )

    # Teachers
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

    # Classes
    cls_alpha = Class(
        name="Alpha",
        visibility="private",
        owner_id=str(teacher_a.id),
        invite_code="ALPHA001",
    )
    await cls_alpha.insert()
    await ClassMembership(
        class_id=str(cls_alpha.id), user_id=str(teacher_a.id), role="teacher",
    ).insert()

    cls_beta = Class(
        name="Beta",
        visibility="private",
        owner_id=str(teacher_b.id),
        invite_code="BETA0001",
    )
    await cls_beta.insert()
    await ClassMembership(
        class_id=str(cls_beta.id), user_id=str(teacher_b.id), role="teacher",
    ).insert()

    # Student in Alpha
    student = User(
        username="stu",
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=int(STUDENT),
    )
    await student.insert()
    await ClassMembership(
        class_id=str(cls_alpha.id), user_id=str(student.id), role="student",
    ).insert()

    # Seed 20 points so deduct tests have a balance to work with
    from gamification.points.service import award_points
    await award_points(str(student.id), str(cls_alpha.id), 20, "submission", "seed")

    # Build FastAPI app with the three gamification routers
    from fastapi import FastAPI
    from gamification.points.router import router as points_router
    from gamification.badges.router import router as badges_router
    from gamification.prizes.router import router as prizes_router

    app = FastAPI()
    app.include_router(points_router)
    app.include_router(badges_router)
    app.include_router(prizes_router)

    yield app, teacher_a, teacher_b, student, cls_alpha, cls_beta
    client.close()


# ── Cross-class rejection ────────────────────────────────────────────────────


async def test_teacher_cannot_deduct_points_in_another_class(cross_class_app):
    """Teacher B tries to deduct points in Alpha (owned by A) → 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, ta, tb, student, cls_alpha, cls_beta = cross_class_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.post(
            "/api/points/deduct",
            json={
                "student_id": str(student.id),
                "class_id": str(cls_alpha.id),
                "amount": 5,
                "reason": "test",
            },
        )
    assert resp.status_code == 403


async def test_teacher_cannot_create_badge_in_another_class(cross_class_app):
    """Teacher B tries to create a badge in Alpha → 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, ta, tb, student, cls_alpha, cls_beta = cross_class_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls_alpha.id}/badges",
            json={
                "name": "Sneaky Badge",
                "description": "Should not be created",
            },
        )
    assert resp.status_code == 403


async def test_teacher_cannot_create_prize_in_another_class(cross_class_app):
    """Teacher B tries to create a prize in Alpha → 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, ta, tb, student, cls_alpha, cls_beta = cross_class_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(tb.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls_alpha.id}/prizes",
            json={
                "title": "Stolen Prize",
                "description": "Should not be created",
                "point_cost": 10,
            },
        )
    assert resp.status_code == 403


# ── Owner teacher positive case ──────────────────────────────────────────────


async def test_owner_teacher_can_deduct_points_in_own_class(cross_class_app):
    """Teacher A deducts points in Alpha (own class) → 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, ta, tb, student, cls_alpha, cls_beta = cross_class_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(ta.id), int(TEACHER)))
        resp = await ac.post(
            "/api/points/deduct",
            json={
                "student_id": str(student.id),
                "class_id": str(cls_alpha.id),
                "amount": 5,
                "reason": "test",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["deducted"] == 5


async def test_deduct_response_balance_is_class_scoped(cross_class_app):
    """Deduct response new_balance reflects only this class, not the global total (FINDING-002)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.points.service import award_points

    app, ta, tb, student, cls_alpha, cls_beta = cross_class_app
    # Student also has points in Beta — these must NOT surface in Alpha's response.
    await award_points(str(student.id), str(cls_beta.id), 100, "submission", "beta_seed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(ta.id), int(TEACHER)))
        resp = await ac.post(
            "/api/points/deduct",
            json={
                "student_id": str(student.id),
                "class_id": str(cls_alpha.id),
                "amount": 5,
                "reason": "test",
            },
        )
    assert resp.status_code == 200
    # Alpha balance = 20 seeded − 5 = 15; Beta's 100 must not leak into the response.
    assert resp.json()["new_balance"] == 15
