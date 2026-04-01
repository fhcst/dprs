"""Tests for TriggerRule CRUD service."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

# Inject a fake dsl_engine module so the local `import dsl_engine` in the
# service resolves without the real PyO3 extension being installed.
_fake_dsl = MagicMock()
sys.modules.setdefault("dsl_engine", _fake_dsl)


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_trigger_rules")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.triggers.models import TriggerRule
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            BadgeDefinition, BadgeAward,
            TriggerRule,
        ],
    )
    yield database
    client.close()


# --- create_trigger_rule ---

@patch("dsl_engine.validate", return_value="[]")
async def test_create_trigger_rule(mock_validate, db):
    from gamification.triggers.service import create_trigger_rule
    from gamification.triggers.models import TriggerRule

    rule = await create_trigger_rule(
        class_id="cls1",
        name="Streak 3",
        expression="checkin.streak >= 3",
        created_by="teacher1",
    )

    assert rule.id is not None
    found = await TriggerRule.get(rule.id)
    assert found is not None
    assert found.class_id == "cls1"
    assert found.name == "Streak 3"
    assert found.expression == "checkin.streak >= 3"
    assert found.created_by == "teacher1"
    assert found.is_active is True


@patch("dsl_engine.validate")
async def test_create_rule_invalid_expression(mock_validate, db):
    import json
    mock_validate.return_value = json.dumps(
        [{"severity": "error", "message": "unexpected token"}]
    )
    from gamification.triggers.service import create_trigger_rule

    with pytest.raises(ValueError, match="Invalid DSL expression"):
        await create_trigger_rule(
            class_id="cls1",
            name="Bad Rule",
            expression="???",
            created_by="teacher1",
        )


# --- update_trigger_rule ---

@patch("dsl_engine.validate", return_value="[]")
async def test_update_trigger_rule(mock_validate, db):
    from gamification.triggers.service import create_trigger_rule, update_trigger_rule

    rule = await create_trigger_rule(
        class_id="cls1",
        name="Old Name",
        expression="checkin.streak >= 3",
        created_by="teacher1",
    )

    updated = await update_trigger_rule(
        rule,
        name="New Name",
        expression="checkin.streak >= 5",
    )

    assert updated.name == "New Name"
    assert updated.expression == "checkin.streak >= 5"

    from gamification.triggers.models import TriggerRule
    persisted = await TriggerRule.get(rule.id)
    assert persisted.name == "New Name"
    assert persisted.expression == "checkin.streak >= 5"


# --- delete_trigger_rule ---

@patch("dsl_engine.validate", return_value="[]")
async def test_delete_trigger_rule(mock_validate, db):
    from gamification.triggers.service import create_trigger_rule, delete_trigger_rule
    from gamification.triggers.models import TriggerRule

    rule = await create_trigger_rule(
        class_id="cls1",
        name="To Delete",
        expression="checkin.streak >= 1",
        created_by="teacher1",
    )
    rule_id = rule.id

    await delete_trigger_rule(rule)

    assert await TriggerRule.get(rule_id) is None


@patch("dsl_engine.validate", return_value="[]")
async def test_delete_rule_bound_to_badge(mock_validate, db):
    from gamification.triggers.service import create_trigger_rule, delete_trigger_rule
    from gamification.badges.models import BadgeDefinition

    rule = await create_trigger_rule(
        class_id="cls1",
        name="Bound Rule",
        expression="checkin.streak >= 3",
        created_by="teacher1",
    )

    badge = BadgeDefinition(
        class_id="cls1",
        name="Streak Badge",
        description="Awarded for streak",
        trigger_rule_id=str(rule.id),
        created_by="teacher1",
    )
    await badge.insert()

    with pytest.raises(ValueError, match="Cannot delete rule"):
        await delete_trigger_rule(rule)


# --- get_rules_for_class ---

@patch("dsl_engine.validate", return_value="[]")
async def test_get_rules_for_class(mock_validate, db):
    from gamification.triggers.service import create_trigger_rule, get_rules_for_class

    await create_trigger_rule(
        class_id="cls1", name="Rule A", expression="a >= 1", created_by="t1",
    )
    await create_trigger_rule(
        class_id="cls1", name="Rule B", expression="b >= 2", created_by="t1",
    )
    await create_trigger_rule(
        class_id="cls2", name="Rule C", expression="c >= 3", created_by="t2",
    )

    cls1_rules = await get_rules_for_class("cls1")
    assert len(cls1_rules) == 2
    names = {r.name for r in cls1_rules}
    assert names == {"Rule A", "Rule B"}

    cls2_rules = await get_rules_for_class("cls2")
    assert len(cls2_rules) == 1
    assert cls2_rules[0].name == "Rule C"
