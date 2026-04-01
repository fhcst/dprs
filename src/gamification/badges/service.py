"""Badge service functions."""
import json
import logging
from datetime import datetime, timedelta, timezone

from gamification.badges.models import BadgeAward, BadgeDefinition

logger = logging.getLogger("uvicorn.error")


async def award_badge(
    badge_id: str,
    student_id: str,
    class_id: str,
    awarded_by: str = "system",
    reason: str | None = None,
) -> BadgeAward | None:
    """Award a badge to a student. Returns None if already held."""
    existing = await BadgeAward.find_one(
        BadgeAward.badge_id == badge_id,
        BadgeAward.student_id == student_id,
    )
    if existing:
        return None  # Badge not awarded if already held

    award = BadgeAward(
        badge_id=badge_id,
        student_id=student_id,
        class_id=class_id,
        awarded_by=awarded_by,
        reason=reason,
    )
    await award.insert()
    return award


async def get_student_badges(student_id: str) -> list[dict]:
    """Return badges earned by a student with definition details."""
    awards = await BadgeAward.find(
        BadgeAward.student_id == student_id,
    ).sort(-BadgeAward.awarded_at).to_list()

    result = []
    for award in awards:
        defn = await BadgeDefinition.get(award.badge_id)
        result.append({
            "award": award,
            "definition": defn,
        })
    return result


async def evaluate_triggers_for_event(student_id: str, event, class_id: str) -> None:
    """Evaluate all triggers (code + DSL) after a reward event and award matching badges."""
    # Path 1: Code triggers via ExtensionRegistry
    await _evaluate_code_triggers(student_id, event, class_id)

    # Path 2: DSL trigger rules
    await _evaluate_dsl_triggers(student_id, event, class_id)


async def _evaluate_code_triggers(student_id: str, event, class_id: str) -> None:
    """Evaluate code-registered BadgeTriggers from ExtensionRegistry."""
    from extensions.protocols.badge import BadgeTrigger, TriggerContext
    from extensions.registry import registry

    triggers = registry.get_all(BadgeTrigger)
    if not triggers:
        return

    badges = await BadgeDefinition.find(
        BadgeDefinition.class_id == class_id,
        BadgeDefinition.trigger_key != None,  # noqa: E711
    ).to_list()

    for key, trigger in triggers.items():
        matching = [b for b in badges if b.trigger_key == key]
        if not matching:
            continue

        ctx = TriggerContext(class_id=class_id)
        should_award = await trigger.evaluate(student_id, event, ctx)
        if should_award:
            for badge in matching:
                await award_badge(
                    badge_id=str(badge.id),
                    student_id=student_id,
                    class_id=class_id,
                    awarded_by="system",
                )


async def _evaluate_dsl_triggers(student_id: str, event, class_id: str) -> None:
    """Evaluate DSL trigger rules for badges with trigger_rule_id."""
    from gamification.triggers.models import TriggerRule

    badges = await BadgeDefinition.find(
        BadgeDefinition.class_id == class_id,
        BadgeDefinition.trigger_rule_id != None,  # noqa: E711
    ).to_list()

    if not badges:
        return

    # Build eval context once for all rules
    ctx = await build_eval_context(student_id, class_id, event)

    for badge in badges:
        rule = await TriggerRule.get(badge.trigger_rule_id)
        if rule is None or not rule.is_active:
            continue

        try:
            import dsl_engine

            result_json = dsl_engine.evaluate(rule.expression, json.dumps(ctx))
            result = json.loads(result_json)

            if result.get("ok") and result.get("result") is True:
                await award_badge(
                    badge_id=str(badge.id),
                    student_id=student_id,
                    class_id=class_id,
                    awarded_by="system",
                )
        except Exception:
            logger.exception(
                "DSL evaluation error for rule %s (badge %s)", rule.id, badge.id
            )


async def build_eval_context(
    student_id: str, class_id: str, event
) -> dict:
    """Build EvalContext dict from class-scoped student data.

    The context contains pre-computed values for all built-in DSL variables.
    No raw data is exposed — only aggregated counts and values.
    """
    from tasks.checkin.models import CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from gamification.points.models import PointTransaction

    now = datetime.now(timezone.utc)

    # Basic counts
    checkin_count = await CheckinRecord.find(
        CheckinRecord.student_id == student_id,
        CheckinRecord.class_id == class_id,
    ).count()

    submission_count = await TaskSubmission.find(
        TaskSubmission.student_id == student_id,
        TaskSubmission.class_id == class_id,
    ).count()

    txns = await PointTransaction.find(
        PointTransaction.student_id == student_id,
        PointTransaction.class_id == class_id,
    ).to_list()
    points = sum(t.amount for t in txns)

    badge_count = await BadgeAward.find(
        BadgeAward.student_id == student_id,
        BadgeAward.class_id == class_id,
    ).count()

    # Checkin streak
    from gamification.badges.router import _calc_checkin_streak
    checkin_streak = await _calc_checkin_streak(student_id, class_id)

    # Event variables
    event_type = getattr(event, "event_type", "unknown")
    if hasattr(event_type, "value"):
        event_type = event_type.value
    event_occurred_at = getattr(event, "occurred_at", now)

    # Day of week for event.occurred_at (0=Monday ~ 6=Sunday)
    day_of_week = event_occurred_at.weekday()

    ctx: dict = {
        "values": {
            "checkin_count": checkin_count,
            "checkin_streak": checkin_streak,
            "submission_count": submission_count,
            "points": points,
            "badge_count": badge_count,
            "event.type": event_type,
            "event.occurred_at.day_of_week": day_of_week,
        }
    }

    # Pre-compute common time windows (7, 14, 30 days)
    for days in [7, 14, 30]:
        cutoff = now - timedelta(days=days)
        sub_w = await TaskSubmission.find(
            TaskSubmission.student_id == student_id,
            TaskSubmission.class_id == class_id,
            TaskSubmission.submitted_at >= cutoff,
        ).count()
        chk_w = await CheckinRecord.find(
            CheckinRecord.student_id == student_id,
            CheckinRecord.class_id == class_id,
            CheckinRecord.checked_in_at >= cutoff,
        ).count()
        ctx["values"][f"submissions_last_{days}_days"] = sub_w
        ctx["values"][f"checkins_last_{days}_days"] = chk_w

    return ctx
