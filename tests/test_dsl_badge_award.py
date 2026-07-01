"""Tests for DSL trigger evaluation in the badge award flow."""
import json
from unittest.mock import MagicMock, patch

import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_dsl_badge_award")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from gamification.points.models import PointTransaction
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.triggers.models import TriggerRule
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            TaskSubmission, PointTransaction,
            BadgeDefinition, BadgeAward, TriggerRule,
        ],
    )
    yield database
    client.close()


@pytest.fixture
async def student(db):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(
        username="stu_dsl",
        hashed_password=hash_password("pw"),
        display_name="DSL Student",
        role="student",
    )
    await u.insert()
    return u


@pytest.fixture
def reward_event(student):
    from extensions.protocols.reward import RewardEvent, RewardEventType
    return RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(student.id),
        class_id="cls1",
        source_id="rec1",
    )


@pytest.fixture
def mock_dsl_engine():
    """Patch the dsl_engine module imported inside _evaluate_dsl_triggers."""
    fake_engine = MagicMock()
    with patch.dict("sys.modules", {"dsl_engine": fake_engine}):
        yield fake_engine


# -------------------------------------------------------------------
# 1. DSL rule triggers badge award
# -------------------------------------------------------------------

async def test_dsl_rule_triggers_badge_award(db, student, reward_event, mock_dsl_engine):
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import evaluate_triggers_for_event
    from gamification.triggers.models import TriggerRule

    rule = TriggerRule(
        class_id="cls1",
        name="streak_3",
        expression="checkin_streak >= 3",
        is_active=True,
        created_by="teacher1",
    )
    await rule.insert()

    badge = BadgeDefinition(
        class_id="cls1",
        name="Streak Master",
        description="3-day streak",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await badge.insert()

    mock_dsl_engine.evaluate.return_value = json.dumps({"ok": True, "result": True})

    await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")

    awards = await BadgeAward.find(
        BadgeAward.student_id == str(student.id),
        BadgeAward.badge_id == str(badge.id),
    ).to_list()
    assert len(awards) == 1
    assert awards[0].awarded_by == "system"


# -------------------------------------------------------------------
# 2. DSL rule returns false -> no award
# -------------------------------------------------------------------

async def test_dsl_rule_false_does_not_award(db, student, reward_event, mock_dsl_engine):
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import evaluate_triggers_for_event
    from gamification.triggers.models import TriggerRule

    rule = TriggerRule(
        class_id="cls1",
        name="streak_10",
        expression="checkin_streak >= 10",
        is_active=True,
        created_by="teacher1",
    )
    await rule.insert()

    badge = BadgeDefinition(
        class_id="cls1",
        name="Streak Legend",
        description="10-day streak",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await badge.insert()

    mock_dsl_engine.evaluate.return_value = json.dumps({"ok": True, "result": False})

    await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")

    awards = await BadgeAward.find(
        BadgeAward.student_id == str(student.id),
        BadgeAward.badge_id == str(badge.id),
    ).to_list()
    assert len(awards) == 0


# -------------------------------------------------------------------
# 3. Code trigger and DSL trigger coexist in the same class
# -------------------------------------------------------------------

async def test_code_trigger_and_dsl_coexist(db, student, reward_event, mock_dsl_engine):
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import evaluate_triggers_for_event
    from gamification.triggers.models import TriggerRule
    from extensions.protocols.badge import BadgeTrigger, TriggerContext
    from extensions.protocols.reward import RewardEvent
    from extensions.registry.core import TestRegistry

    # --- Code trigger implementation that always awards ---
    class AlwaysTrueTrigger:
        async def evaluate(
            self, student_id: str, event: RewardEvent, context: TriggerContext
        ) -> bool:
            return True

    # Badge driven by code trigger
    code_badge = BadgeDefinition(
        class_id="cls1",
        name="Code Badge",
        description="Awarded via code trigger",
        trigger_key="always_true",
        created_by="teacher1",
    )
    await code_badge.insert()

    # Badge driven by DSL trigger
    rule = TriggerRule(
        class_id="cls1",
        name="dsl_rule",
        expression="checkin_count >= 1",
        is_active=True,
        created_by="teacher1",
    )
    await rule.insert()

    dsl_badge = BadgeDefinition(
        class_id="cls1",
        name="DSL Badge",
        description="Awarded via DSL trigger",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await dsl_badge.insert()

    mock_dsl_engine.evaluate.return_value = json.dumps({"ok": True, "result": True})

    with TestRegistry() as test_reg:
        test_reg.register(BadgeTrigger, "always_true", AlwaysTrueTrigger())
        await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")

    # Both badges should be awarded
    code_awards = await BadgeAward.find(
        BadgeAward.badge_id == str(code_badge.id),
        BadgeAward.student_id == str(student.id),
    ).to_list()
    assert len(code_awards) == 1

    dsl_awards = await BadgeAward.find(
        BadgeAward.badge_id == str(dsl_badge.id),
        BadgeAward.student_id == str(student.id),
    ).to_list()
    assert len(dsl_awards) == 1


# -------------------------------------------------------------------
# 4. Inactive DSL rule is skipped (evaluate not called, no award)
# -------------------------------------------------------------------

async def test_inactive_dsl_rule_skipped(db, student, reward_event, mock_dsl_engine):
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import evaluate_triggers_for_event
    from gamification.triggers.models import TriggerRule

    rule = TriggerRule(
        class_id="cls1",
        name="inactive_rule",
        expression="checkin_count >= 1",
        is_active=False,
        created_by="teacher1",
    )
    await rule.insert()

    badge = BadgeDefinition(
        class_id="cls1",
        name="Ghost Badge",
        description="Should never be awarded",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await badge.insert()

    await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")

    # dsl_engine.evaluate should NOT have been called
    mock_dsl_engine.evaluate.assert_not_called()

    awards = await BadgeAward.find(
        BadgeAward.student_id == str(student.id),
        BadgeAward.badge_id == str(badge.id),
    ).to_list()
    assert len(awards) == 0


# -------------------------------------------------------------------
# 5. Duplicate award prevention — trigger fires again, no second award
# -------------------------------------------------------------------

async def test_duplicate_award_prevention(db, student, reward_event, mock_dsl_engine):
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.badges.service import evaluate_triggers_for_event
    from gamification.triggers.models import TriggerRule

    rule = TriggerRule(
        class_id="cls1",
        name="dup_rule",
        expression="checkin_count >= 1",
        is_active=True,
        created_by="teacher1",
    )
    await rule.insert()

    badge = BadgeDefinition(
        class_id="cls1",
        name="Unique Badge",
        description="Only once",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await badge.insert()

    mock_dsl_engine.evaluate.return_value = json.dumps({"ok": True, "result": True})

    # First evaluation — should award
    await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")
    awards_after_first = await BadgeAward.find(
        BadgeAward.student_id == str(student.id),
        BadgeAward.badge_id == str(badge.id),
    ).to_list()
    assert len(awards_after_first) == 1

    # Second evaluation — trigger fires again but no duplicate
    await evaluate_triggers_for_event(str(student.id), reward_event, "cls1")
    awards_after_second = await BadgeAward.find(
        BadgeAward.student_id == str(student.id),
        BadgeAward.badge_id == str(badge.id),
    ).to_list()
    assert len(awards_after_second) == 1
