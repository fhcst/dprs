"""Tests for students/stats streak logic and BadgeDefinition trigger mutual exclusion."""
import pytest
from datetime import date, datetime, timedelta, timezone

from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_trigger_rules")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from gamification.points.models import PointTransaction, ClassPointConfig
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.triggers.models import TriggerRule
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            TaskSubmission,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward,
            TriggerRule,
        ],
    )
    yield database
    client.close()


# ---------------------------------------------------------------------------
# 8.3  _calc_checkin_streak — direct logic tests (no HTTP)
# ---------------------------------------------------------------------------


async def test_calc_checkin_streak(db):
    """Consecutive check-in records should produce the correct streak count."""
    from tasks.checkin.models import CheckinRecord
    from gamification.badges.router import _calc_checkin_streak

    student_id = "stu1"
    class_id = "cls1"
    today = date.today()

    # Create 5 consecutive days of check-ins ending today
    for i in range(5):
        d = today - timedelta(days=i)
        rec = CheckinRecord(
            student_id=student_id,
            class_id=class_id,
            checkin_date=d,
            checked_in_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
        )
        await rec.insert()

    streak = await _calc_checkin_streak(student_id, class_id)
    assert streak == 5


async def test_calc_checkin_streak_gap(db):
    """A gap in check-in dates should reset the streak."""
    from tasks.checkin.models import CheckinRecord
    from gamification.badges.router import _calc_checkin_streak

    student_id = "stu2"
    class_id = "cls1"
    today = date.today()

    # Days: today, yesterday, day-before-yesterday (streak = 3)
    # Then skip one day, then two more days (should NOT count)
    consecutive_days = [0, 1, 2]  # streak of 3
    gap_days = [4, 5]  # day 3 is missing — these don't count

    for i in consecutive_days + gap_days:
        d = today - timedelta(days=i)
        rec = CheckinRecord(
            student_id=student_id,
            class_id=class_id,
            checkin_date=d,
            checked_in_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
        )
        await rec.insert()

    streak = await _calc_checkin_streak(student_id, class_id)
    assert streak == 3


# ---------------------------------------------------------------------------
# 8.4  BadgeDefinition trigger_key / trigger_rule_id mutual exclusion
# ---------------------------------------------------------------------------


async def test_badge_trigger_key_only(db):
    """BadgeDefinition with only trigger_key set should succeed."""
    from gamification.badges.models import BadgeDefinition

    badge = BadgeDefinition(
        class_id="cls1",
        name="Key Only",
        description="Uses trigger_key",
        trigger_key="consecutive_checkin",
        trigger_rule_id=None,
        created_by="teacher1",
    )
    await badge.insert()

    found = await BadgeDefinition.get(badge.id)
    assert found is not None
    assert found.trigger_key == "consecutive_checkin"
    assert found.trigger_rule_id is None


async def test_badge_trigger_rule_id_only(db):
    """BadgeDefinition with only trigger_rule_id set should succeed."""
    from gamification.badges.models import BadgeDefinition

    badge = BadgeDefinition(
        class_id="cls1",
        name="Rule Only",
        description="Uses trigger_rule_id",
        trigger_key=None,
        trigger_rule_id="rule_abc123",
        created_by="teacher1",
    )
    await badge.insert()

    found = await BadgeDefinition.get(badge.id)
    assert found is not None
    assert found.trigger_key is None
    assert found.trigger_rule_id == "rule_abc123"


async def test_badge_both_triggers_raises(db):
    """BadgeDefinition with both trigger_key AND trigger_rule_id must raise ValueError."""
    from gamification.badges.models import BadgeDefinition
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="mutually exclusive"):
        BadgeDefinition(
            class_id="cls1",
            name="Both Triggers",
            description="Should fail",
            trigger_key="consecutive_checkin",
            trigger_rule_id="rule_abc123",
            created_by="teacher1",
        )


async def test_badge_neither_trigger(db):
    """BadgeDefinition with both triggers None should succeed (manual award)."""
    from gamification.badges.models import BadgeDefinition

    badge = BadgeDefinition(
        class_id="cls1",
        name="Manual Badge",
        description="Awarded manually",
        trigger_key=None,
        trigger_rule_id=None,
        created_by="teacher1",
    )
    await badge.insert()

    found = await BadgeDefinition.get(badge.id)
    assert found is not None
    assert found.trigger_key is None
    assert found.trigger_rule_id is None
