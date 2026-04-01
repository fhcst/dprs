"""Trigger rule service functions."""
import json
from datetime import datetime, timezone

from gamification.badges.models import BadgeDefinition
from gamification.triggers.models import TriggerRule


async def create_trigger_rule(
    class_id: str,
    name: str,
    expression: str,
    created_by: str,
) -> TriggerRule:
    """Create a new trigger rule after validating the DSL expression."""
    _validate_expression(expression)

    rule = TriggerRule(
        class_id=class_id,
        name=name,
        expression=expression,
        created_by=created_by,
    )
    await rule.insert()
    return rule


async def update_trigger_rule(
    rule: TriggerRule,
    name: str | None = None,
    expression: str | None = None,
    is_active: bool | None = None,
) -> TriggerRule:
    """Update an existing trigger rule."""
    if expression is not None:
        _validate_expression(expression)
        rule.expression = expression

    if name is not None:
        rule.name = name
    if is_active is not None:
        rule.is_active = is_active

    rule.updated_at = datetime.now(timezone.utc)
    await rule.save()
    return rule


async def delete_trigger_rule(rule: TriggerRule) -> None:
    """Delete a trigger rule. Raises ValueError if bound to any badge."""
    bound_badges = await BadgeDefinition.find(
        BadgeDefinition.trigger_rule_id == str(rule.id),
    ).to_list()

    if bound_badges:
        badge_names = [b.name for b in bound_badges]
        raise ValueError(
            f"Cannot delete rule: bound to badges: {', '.join(badge_names)}"
        )

    await rule.delete()


async def get_rules_for_class(class_id: str) -> list[TriggerRule]:
    """List all trigger rules for a class."""
    return await TriggerRule.find(
        TriggerRule.class_id == class_id,
    ).sort(-TriggerRule.created_at).to_list()


async def get_rule_with_badge_count(rule: TriggerRule) -> dict:
    """Return rule data with count of bound badges."""
    count = await BadgeDefinition.find(
        BadgeDefinition.trigger_rule_id == str(rule.id),
    ).count()
    return {
        "rule": rule,
        "bound_badge_count": count,
    }


def _validate_expression(expression: str) -> None:
    """Validate DSL expression using the Rust engine via PyO3.
    Raises ValueError with details if validation fails or engine is unavailable."""
    try:
        import dsl_engine
    except ImportError:
        raise ValueError(
            "DSL engine (dsl_engine) is not installed. "
            "Please run 'maturin develop --features python' in crates/dsl-engine/"
        )

    result_json = dsl_engine.validate(expression)
    diagnostics = json.loads(result_json)

    errors = [d for d in diagnostics if d.get("severity") == "error"]
    if errors:
        messages = "; ".join(d["message"] for d in errors)
        raise ValueError(f"Invalid DSL expression: {messages}")
