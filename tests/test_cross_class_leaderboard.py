"""Tests for cross-class leaderboard membership enforcement."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


@pytest.fixture
async def leaderboard_app():
    """Teacher manages class Alpha; outsider student is NOT a member."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT
    from gamification.points.models import PointTransaction, ClassPointConfig
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.prizes.models import Prize

    client = AsyncMongoMockClient()
    db = client.get_database("test_cross_leaderboard")
    await init_beanie(
        database=db,
        document_models=[
            User, Class, ClassMembership,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
            Prize,
        ],
    )

    # Teacher who owns Alpha
    teacher = User(
        username="teacher1",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    # Class Alpha
    alpha = Class(
        name="Alpha",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="ALPHA001",
        leaderboard_enabled=True,
    )
    await alpha.insert()
    await ClassMembership(
        class_id=str(alpha.id), user_id=str(teacher.id), role="teacher",
    ).insert()

    # Member student — enrolled in Alpha
    member = User(
        username="member_stu",
        hashed_password=hash_password("pw"),
        display_name="Member",
        permissions=int(STUDENT),
    )
    await member.insert()
    await ClassMembership(
        class_id=str(alpha.id), user_id=str(member.id), role="student",
    ).insert()

    # Non-member student — NOT in Alpha
    outsider = User(
        username="outsider_stu",
        hashed_password=hash_password("pw"),
        display_name="Outsider",
        permissions=int(STUDENT),
    )
    await outsider.insert()

    from fastapi import FastAPI
    from gamification.leaderboard.router import router as lb_router

    app = FastAPI()
    app.include_router(lb_router)

    yield app, teacher, member, outsider, alpha
    client.close()


async def test_non_member_cannot_view_leaderboard(leaderboard_app):
    """Non-member student requesting class leaderboard receives 403."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import STUDENT

    app, teacher, member, outsider, alpha = leaderboard_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(outsider.id), int(STUDENT)))
        resp = await ac.get(f"/classes/{alpha.id}/leaderboard")
    assert resp.status_code == 403


async def test_member_can_view_leaderboard(leaderboard_app):
    """Member student can view class leaderboard — 200."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import STUDENT

    app, teacher, member, outsider, alpha = leaderboard_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(member.id), int(STUDENT)))
        resp = await ac.get(f"/classes/{alpha.id}/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["visible"] is True
    assert "leaderboard" in data


async def test_non_member_cannot_view_leaderboard_page(leaderboard_app):
    """Non-member requesting the leaderboard PAGE receives 403 (FINDING-003).

    The page route previously gated only on a permission flag, letting any
    teacher-permission holder (and, via leaderboard_enabled, outsiders) browse
    another class's ranking. It must mirror the API route's membership check.
    """
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import STUDENT

    app, teacher, member, outsider, alpha = leaderboard_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(outsider.id), int(STUDENT)))
        resp = await ac.get(f"/pages/classes/{alpha.id}/leaderboard")
    assert resp.status_code == 403
