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


# ── Helpers for revoke/detail tests ──────────────────────────────────────────

@pytest.fixture
async def full_app():
    """Teacher + student in same class, manual badge, auto-trigger badge; yields app + entities."""
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER, STUDENT
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from gamification.points.models import PointTransaction

    client = AsyncMongoMockClient()
    database = client.get_database("test_badge_revoke")
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            TaskSubmission, BadgeDefinition, BadgeAward, PointTransaction,
        ],
    )

    teacher = User(
        username="teacher_rv",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await teacher.insert()

    outsider_teacher = User(
        username="other_teacher",
        hashed_password=hash_password("pw"),
        display_name="Other Teacher",
        permissions=int(TEACHER),
    )
    await outsider_teacher.insert()

    stu = User(
        username="stu_rv",
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=int(STUDENT),
    )
    await stu.insert()

    cls = Class(
        name="RevClass",
        visibility="private",
        owner_id=str(teacher.id),
        invite_code="RVCL0001",
    )
    await cls.insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()
    await ClassMembership(class_id=str(cls.id), user_id=str(stu.id), role="student").insert()

    manual_badge = BadgeDefinition(
        class_id=str(cls.id),
        name="Manual Badge",
        description="Manual only",
        created_by=str(teacher.id),
    )
    await manual_badge.insert()

    auto_badge = BadgeDefinition(
        class_id=str(cls.id),
        name="Auto Badge",
        description="Automatic",
        trigger_key="checkin_streak_3",
        created_by=str(teacher.id),
    )
    await auto_badge.insert()

    from fastapi import FastAPI
    from gamification.badges.router import router as badges_router

    app = FastAPI()
    app.include_router(badges_router)

    yield app, teacher, outsider_teacher, stu, cls, manual_badge, auto_badge
    client.close()


# ── 6.4: soft delete filter tests ────────────────────────────────────────────

async def test_revoked_badge_not_shown_to_student(db, student):
    """Revoked award must not appear in get_student_badges."""
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import award_badge, get_student_badges, revoke_badge

    badge = BadgeDefinition(class_id="cls1", name="Rev", description="x", created_by="t")
    await badge.insert()

    award = await award_badge(str(badge.id), str(student.id), "cls1")
    assert award is not None

    result_before = await get_student_badges(str(student.id))
    assert len(result_before) == 1

    await revoke_badge(str(award.id), str(badge.id), "cls1", revoked_by="teacher")

    result_after = await get_student_badges(str(student.id))
    assert len(result_after) == 0


async def test_revoked_award_excluded_from_active_awards_query(db, student):
    """active_awards_query must exclude revoked awards."""
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import award_badge, active_awards_query, revoke_badge

    badge = BadgeDefinition(class_id="cls1", name="AQ", description="x", created_by="t")
    await badge.insert()

    award = await award_badge(str(badge.id), str(student.id), "cls1")
    assert award is not None

    count_before = await active_awards_query(BadgeAward.student_id == str(student.id)).count()
    assert count_before == 1

    await revoke_badge(str(award.id), str(badge.id), "cls1", revoked_by="teacher")

    count_after = await active_awards_query(BadgeAward.student_id == str(student.id)).count()
    assert count_after == 0


# ── 6.3: re-award tests ───────────────────────────────────────────────────────

async def test_reawarding_after_revoke_succeeds(db, student):
    """After revoke, award_badge should succeed again (re-awarding a previously revoked badge)."""
    from gamification.badges.models import BadgeDefinition
    from gamification.badges.service import award_badge, revoke_badge

    badge = BadgeDefinition(class_id="cls1", name="R2", description="x", created_by="t")
    await badge.insert()

    first = await award_badge(str(badge.id), str(student.id), "cls1")
    assert first is not None

    await revoke_badge(str(first.id), str(badge.id), "cls1", revoked_by="teacher")

    second = await award_badge(str(badge.id), str(student.id), "cls1")
    assert second is not None, "Should be able to re-award after revoke"
    assert second.id != first.id


async def test_award_badge_duplicate_active_returns_none(db, student):
    """award_badge returns None when student already holds active award (student with active award cannot receive duplicate)."""
    from gamification.badges.models import BadgeDefinition
    from gamification.badges.service import award_badge

    badge = BadgeDefinition(class_id="cls1", name="Dup", description="x", created_by="t")
    await badge.insert()

    first = await award_badge(str(badge.id), str(student.id), "cls1")
    assert first is not None
    second = await award_badge(str(badge.id), str(student.id), "cls1")
    assert second is None


# ── 6.1: revoke endpoint tests ───────────────────────────────────────────────

async def test_revoke_endpoint_revokes_active_award(full_app):
    """Teacher revokes an active badge award -> 200 (teacher revokes badge award)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.service import award_badge

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    award = await award_badge(str(manual_badge.id), str(stu.id), str(cls.id))
    assert award is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{manual_badge.id}/revoke",
            json={"award_id": str(award.id)},
        )
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True


async def test_revoke_endpoint_already_revoked_returns_409(full_app):
    """Revoking an already-revoked award -> 409 (teacher attempts to revoke already-revoked award)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.service import award_badge, revoke_badge

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    award = await award_badge(str(manual_badge.id), str(stu.id), str(cls.id))
    await revoke_badge(str(award.id), str(manual_badge.id), str(cls.id), revoked_by=str(teacher.id))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{manual_badge.id}/revoke",
            json={"award_id": str(award.id)},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Award already revoked"


async def test_revoke_endpoint_wrong_class_award_returns_404(full_app):
    """Revoke with award_id belonging to different class -> 404 (teacher attempts to revoke award from another class)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.models import BadgeAward

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    # Create award directly with a different class_id
    from datetime import datetime, timezone
    foreign_award = BadgeAward(
        badge_id=str(manual_badge.id),
        student_id=str(stu.id),
        class_id="other_class",
        awarded_by=str(teacher.id),
    )
    await foreign_award.insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{manual_badge.id}/revoke",
            json={"award_id": str(foreign_award.id)},
        )
    assert resp.status_code == 404


async def test_revoke_endpoint_non_managing_teacher_returns_403(full_app):
    """Non-managing teacher tries to revoke -> 403 (non-managing teacher attempts to revoke)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.service import award_badge

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    award = await award_badge(str(manual_badge.id), str(stu.id), str(cls.id))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(outsider.id), int(TEACHER)))
        resp = await ac.post(
            f"/classes/{cls.id}/badges/{manual_badge.id}/revoke",
            json={"award_id": str(award.id)},
        )
    assert resp.status_code == 403


# ── 6.2: badge detail API tests ──────────────────────────────────────────────

async def test_badge_detail_api_returns_awarded_and_not_awarded(full_app):
    """Teacher fetches badge detail for own class (badge detail API)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.service import award_badge

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    await award_badge(str(manual_badge.id), str(stu.id), str(cls.id))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/{manual_badge.id}/detail")

    assert resp.status_code == 200
    data = resp.json()
    assert data["badge"]["id"] == str(manual_badge.id)
    assert data["is_manual"] is True
    assert len(data["awarded"]) == 1
    assert data["awarded"][0]["student_id"] == str(stu.id)
    assert "award_id" in data["awarded"][0]
    assert "awarded_at" in data["awarded"][0]
    assert len(data["not_awarded"]) == 0


async def test_badge_detail_api_not_awarded_list(full_app):
    """Not-awarded list shows students who don't hold the badge."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    # No awards yet

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/{manual_badge.id}/detail")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["awarded"]) == 0
    assert len(data["not_awarded"]) == 1
    assert data["not_awarded"][0]["student_id"] == str(stu.id)


async def test_badge_detail_is_manual_false_for_auto_badge(full_app):
    """Auto-trigger badge returns is_manual=False."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/{auto_badge.id}/detail")

    assert resp.status_code == 200
    assert resp.json()["is_manual"] is False


async def test_badge_detail_non_managing_teacher_returns_403(full_app):
    """Teacher who doesn't manage class gets 403 (teacher fetches badge detail for another class)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(outsider.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/{manual_badge.id}/detail")

    assert resp.status_code == 403


async def test_badge_detail_badge_not_found_returns_404(full_app):
    """Non-existent badge_id returns 404 (badge not found or wrong class)."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/000000000000000000000001/detail")

    assert resp.status_code == 404


async def test_badge_detail_revoked_award_not_in_awarded(full_app):
    """Revoked award must not appear in the awarded list."""
    from httpx import AsyncClient, ASGITransport
    from core.auth.permissions import TEACHER
    from gamification.badges.service import award_badge, revoke_badge

    app, teacher, outsider, stu, cls, manual_badge, auto_badge = full_app
    award = await award_badge(str(manual_badge.id), str(stu.id), str(cls.id))
    await revoke_badge(str(award.id), str(manual_badge.id), str(cls.id), revoked_by=str(teacher.id))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", _token(str(teacher.id), int(TEACHER)))
        resp = await ac.get(f"/classes/{cls.id}/badges/{manual_badge.id}/detail")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["awarded"]) == 0
    assert len(data["not_awarded"]) == 1
