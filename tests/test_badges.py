"""Tests for badge system."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_badges")
    from core.users.models import User
    from core.classes.models import Class
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from gamification.badges.models import BadgeDefinition, BadgeAward
    await init_beanie(
        database=database,
        document_models=[
            User, Class, CheckinConfig, DailyCheckinOverride, CheckinRecord,
            TaskSubmission, BadgeDefinition, BadgeAward,
        ],
    )
    yield database
    client.close()


@pytest.fixture
async def student(db):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(username="stu", hashed_password=hash_password("pw"), display_name="S", role="student")
    await u.insert()
    return u


# --- BadgeDefinition ---

async def test_create_badge_definition(db, student):
    from gamification.badges.models import BadgeDefinition
    badge = BadgeDefinition(
        class_id="cls1",
        name="First Steps",
        description="Check in for the first time",
        created_by=str(student.id),
    )
    await badge.insert()
    found = await BadgeDefinition.get(badge.id)
    assert found is not None
    assert found.name == "First Steps"


# --- award_badge ---

async def test_award_badge_creates_record(db, student):
    from gamification.badges.models import BadgeDefinition
    from gamification.badges.service import award_badge

    badge = BadgeDefinition(class_id="cls1", name="X", description="Y", created_by="t1")
    await badge.insert()

    award = await award_badge(str(badge.id), str(student.id), "cls1")
    assert award is not None
    assert award.student_id == str(student.id)


async def test_award_badge_not_duplicated(db, student):
    from gamification.badges.models import BadgeDefinition
    from gamification.badges.service import award_badge

    badge = BadgeDefinition(class_id="cls1", name="X", description="Y", created_by="t1")
    await badge.insert()

    first = await award_badge(str(badge.id), str(student.id), "cls1")
    second = await award_badge(str(badge.id), str(student.id), "cls1")
    assert first is not None
    assert second is None  # Badge not awarded if already held


# --- get_student_badges ---

async def test_get_student_badges(db, student):
    from gamification.badges.models import BadgeDefinition
    from gamification.badges.service import award_badge, get_student_badges

    badge = BadgeDefinition(class_id="cls1", name="Hero", description="Brave", created_by="t1")
    await badge.insert()
    await award_badge(str(badge.id), str(student.id), "cls1", reason="manual")

    result = await get_student_badges(str(student.id))
    assert len(result) == 1
    assert result[0]["definition"].name == "Hero"
    assert result[0]["award"].reason == "manual"


# --- ConsecutiveCheckinTrigger ---

async def test_consecutive_checkin_trigger_false_when_not_enough(db, student):
    from gamification.badges.triggers import ConsecutiveCheckinTrigger
    from extensions.protocols.badge import TriggerContext
    from extensions.protocols.reward import RewardEvent, RewardEventType

    trigger = ConsecutiveCheckinTrigger(required_streak=3)
    event = RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(student.id),
        class_id="cls1",
        source_id="rec1",
    )
    ctx = TriggerContext(class_id="cls1")
    result = await trigger.evaluate(str(student.id), event, ctx)
    assert result is False


async def test_consecutive_checkin_trigger_true_when_streak_met(db, student):
    from datetime import datetime, timezone, timedelta
    from tasks.checkin.models import CheckinRecord
    from gamification.badges.triggers import ConsecutiveCheckinTrigger
    from extensions.protocols.badge import TriggerContext
    from extensions.protocols.reward import RewardEvent, RewardEventType

    now = datetime.now(timezone.utc)
    for i in range(3):
        rec = CheckinRecord(
            student_id=str(student.id),
            class_id="cls1",
            checked_in_at=now - timedelta(days=i),
            checkin_date=(now - timedelta(days=i)).date(),
        )
        await rec.insert()

    trigger = ConsecutiveCheckinTrigger(required_streak=3)
    event = RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(student.id),
        class_id="cls1",
        source_id="rec1",
    )
    ctx = TriggerContext(class_id="cls1")
    result = await trigger.evaluate(str(student.id), event, ctx)
    assert result is True


# --- SubmissionCountTrigger ---

async def test_submission_count_trigger(db, student):
    from gamification.badges.triggers import SubmissionCountTrigger
    from extensions.protocols.badge import TriggerContext
    from extensions.protocols.reward import RewardEvent, RewardEventType
    from tasks.submissions.models import TaskSubmission
    from datetime import date

    for i in range(5):
        sub = TaskSubmission(
            template_id="tmpl1",
            template_snapshot={"name": "T"},
            field_values={},
            student_id=str(student.id),
            class_id="cls1",
            date=date.today(),
        )
        await sub.insert()

    trigger = SubmissionCountTrigger(required_count=5)
    event = RewardEvent(
        event_type=RewardEventType.SUBMISSION,
        student_id=str(student.id),
        class_id="cls1",
        source_id="sub1",
    )
    ctx = TriggerContext(class_id="cls1")
    result = await trigger.evaluate(str(student.id), event, ctx)
    assert result is True


# --- manual_award_badge endpoint IDOR tests ---


def _token(user_id: str, permissions: int) -> str:
    from core.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, permissions=permissions)


@pytest.fixture
async def award_app():
    """Teacher owns a class with a badge; yields app + entities."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord
    from tasks.submissions.models import TaskSubmission

    client = AsyncMongoMockClient()
    database = client.get_database("test_badge_award_idor")
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            TaskSubmission, BadgeDefinition, BadgeAward,
        ],
    )

    teacher = User(
        username="teacher1",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    cls = Class(
        name="TestClass",
        visibility="private",
        owner_id=str(teacher.id),
        invite_code="TCLS0001",
    )
    await cls.insert()
    await ClassMembership(
        class_id=str(cls.id), user_id=str(teacher.id), role="teacher",
    ).insert()

    badge = BadgeDefinition(
        class_id=str(cls.id),
        name="Manual Badge",
        description="Awarded manually",
        created_by=str(teacher.id),
    )
    await badge.insert()

    from fastapi import FastAPI
    from gamification.badges.router import router as badges_router

    app = FastAPI()
    app.include_router(badges_router)

    yield app, teacher, cls, badge
    client.close()


async def test_manual_award_badge_to_class_student_succeeds(award_app):
    """Award badge to a student who IS a member of the class -> 200."""
    from httpx import AsyncClient, ASGITransport
    from core.users.models import User
    from core.classes.models import ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT

    app, teacher, cls, badge = award_app

    stu = User(
        username="stu_member",
        hashed_password=hash_password("pw"),
        display_name="Stu Member",
        permissions=int(STUDENT),
    )
    await stu.insert()
    await ClassMembership(
        class_id=str(cls.id), user_id=str(stu.id), role="student",
    ).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{badge.id}/award",
            json={"student_id": str(stu.id)},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["awarded"] is True
    assert "award_id" in data


async def test_manual_award_badge_to_non_member_returns_403(award_app):
    """Award badge to a student who is NOT a member of the class -> 403."""
    from httpx import AsyncClient, ASGITransport
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT

    app, teacher, cls, badge = award_app

    outsider = User(
        username="outsider",
        hashed_password=hash_password("pw"),
        display_name="Outsider",
        permissions=int(STUDENT),
    )
    await outsider.insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{badge.id}/award",
            json={"student_id": str(outsider.id)},
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Student is not a member of this class"


async def test_manual_award_badge_to_teacher_member_returns_403(award_app):
    """Award badge to a user who is a member but with role 'teacher' -> 403."""
    from httpx import AsyncClient, ASGITransport
    from core.users.models import User
    from core.classes.models import ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER

    app, teacher, cls, badge = award_app

    other_teacher = User(
        username="teacher2",
        hashed_password=hash_password("pw"),
        display_name="Teacher 2",
        permissions=int(TEACHER),
    )
    await other_teacher.insert()
    await ClassMembership(
        class_id=str(cls.id), user_id=str(other_teacher.id), role="teacher",
    ).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{badge.id}/award",
            json={"student_id": str(other_teacher.id)},
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Student is not a member of this class"
