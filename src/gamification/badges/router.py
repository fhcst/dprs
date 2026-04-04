"""Badges router."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_OWN_CLASS, MANAGE_TASKS
from core.classes.models import Class, ClassMembership
from core.classes.service import can_manage_class
from core.users.models import User
from gamification.badges.models import BadgeAward, BadgeDefinition
from gamification.badges.service import award_badge, get_student_badges
from gamification.points.models import PointTransaction
from gamification.triggers.service import get_rules_for_class
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage
from tasks.checkin.models import CheckinRecord
from tasks.submissions.models import TaskSubmission

router = APIRouter(tags=["badges"])


class BadgeCreateRequest(BaseModel):
    name: str
    description: str
    icon: str = "🏅"
    trigger_key: Optional[str] = None
    trigger_rule_id: Optional[str] = None


class BadgeUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    trigger_key: Optional[str] = None
    trigger_rule_id: Optional[str] = None


class ManualAwardRequest(BaseModel):
    student_id: str
    reason: Optional[str] = None


@router.post("/classes/{class_id}/badges", status_code=status.HTTP_201_CREATED)
async def create_badge(
    class_id: str,
    body: BadgeCreateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    try:
        badge = BadgeDefinition(
            class_id=class_id,
            name=body.name,
            description=body.description,
            icon=body.icon,
            trigger_key=body.trigger_key,
            trigger_rule_id=body.trigger_rule_id,
            created_by=str(teacher.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    await badge.insert()
    return {"id": str(badge.id), "name": badge.name}


@router.put("/classes/{class_id}/badges/{badge_id}")
async def update_badge(
    class_id: str,
    badge_id: str,
    body: BadgeUpdateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    badge = await BadgeDefinition.get(badge_id)
    if badge is None or badge.class_id != class_id:
        raise HTTPException(status_code=404, detail="Badge not found")

    if body.name is not None:
        badge.name = body.name
    if body.description is not None:
        badge.description = body.description
    if body.icon is not None:
        badge.icon = body.icon

    # Handle trigger source: clear the other when one is set
    if body.trigger_key is not None:
        badge.trigger_key = body.trigger_key or None
        badge.trigger_rule_id = None
    elif body.trigger_rule_id is not None:
        badge.trigger_rule_id = body.trigger_rule_id or None
        badge.trigger_key = None

    try:
        badge.model_validate(badge.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )

    await badge.save()
    return {"id": str(badge.id), "name": badge.name}


@router.delete("/classes/{class_id}/badges/{badge_id}")
async def delete_badge(
    class_id: str,
    badge_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    badge = await BadgeDefinition.get(badge_id)
    if badge is None or badge.class_id != class_id:
        raise HTTPException(status_code=404, detail="Badge not found")

    # Prevent deletion if badge has been awarded
    award_count = await BadgeAward.find(
        BadgeAward.badge_id == badge_id,
        BadgeAward.class_id == class_id,
    ).count()
    if award_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete badge: already awarded to {award_count} student(s)",
        )

    await badge.delete()
    return {"deleted": True}


@router.post("/classes/{class_id}/badges/{badge_id}/award")
async def manual_award_badge(
    class_id: str,
    badge_id: str,
    body: ManualAwardRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    badge = await BadgeDefinition.get(badge_id)
    if badge is None or badge.class_id != class_id:
        raise HTTPException(status_code=404, detail="Badge not found")

    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == body.student_id,
        ClassMembership.role == "student",
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student is not a member of this class",
        )

    award = await award_badge(
        badge_id=badge_id,
        student_id=body.student_id,
        class_id=class_id,
        awarded_by=str(teacher.id),
        reason=body.reason,
    )
    if award is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student already holds this badge",
        )
    return {"awarded": True, "award_id": str(award.id)}


@router.get("/students/me/badges")
async def my_badges(user: User = Depends(get_current_user)):
    badges = await get_student_badges(str(user.id))
    return [
        {
            "badge_id": item["award"].badge_id,
            "name": item["definition"].name if item["definition"] else "Unknown",
            "icon": item["definition"].icon if item["definition"] else "🏅",
            "description": item["definition"].description if item["definition"] else "",
            "awarded_at": item["award"].awarded_at.isoformat(),
            "reason": item["award"].reason,
        }
        for item in badges
    ]


@router.get("/classes/{class_id}/students/stats")
async def class_student_stats(
    class_id: str,
    windows: Optional[str] = Query(None, description="Comma-separated day counts, e.g. 7,30"),
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    """Return aggregated student stats for dry-run rule testing."""
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Parse time windows
    window_days: list[int] = []
    if windows:
        window_days = [int(w.strip()) for w in windows.split(",") if w.strip().isdigit()]

    # Get all student members
    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id,
        ClassMembership.role == "student",
    ).to_list()

    now = datetime.now(timezone.utc)
    results = []
    for m in memberships:
        sid = m.user_id
        student_user = await User.get(sid)
        display_name = student_user.display_name if student_user else sid

        # Aggregate counts
        checkin_count = await CheckinRecord.find(
            CheckinRecord.student_id == sid,
            CheckinRecord.class_id == class_id,
        ).count()

        submission_count = await TaskSubmission.find(
            TaskSubmission.student_id == sid,
            TaskSubmission.class_id == class_id,
        ).count()

        # Points balance
        txns = await PointTransaction.find(
            PointTransaction.student_id == sid,
            PointTransaction.class_id == class_id,
        ).to_list()
        points = sum(t.amount for t in txns)

        badge_count = await BadgeAward.find(
            BadgeAward.student_id == sid,
            BadgeAward.class_id == class_id,
        ).count()

        # Checkin streak (consecutive days ending today)
        checkin_streak = await _calc_checkin_streak(sid, class_id)

        entry: dict = {
            "student_id": sid,
            "name": display_name,
            "checkin_count": checkin_count,
            "checkin_streak": checkin_streak,
            "submission_count": submission_count,
            "points": points,
            "badge_count": badge_count,
        }

        # Time window pre-computations
        for days in window_days:
            cutoff = now - timedelta(days=days)
            sub_window = await TaskSubmission.find(
                TaskSubmission.student_id == sid,
                TaskSubmission.class_id == class_id,
                TaskSubmission.submitted_at >= cutoff,
            ).count()
            chk_window = await CheckinRecord.find(
                CheckinRecord.student_id == sid,
                CheckinRecord.class_id == class_id,
                CheckinRecord.checked_in_at >= cutoff,
            ).count()
            entry[f"submissions_last_{days}_days"] = sub_window
            entry[f"checkins_last_{days}_days"] = chk_window

        results.append(entry)

    return results


async def _calc_checkin_streak(student_id: str, class_id: str) -> int:
    """Calculate consecutive check-in days ending at today."""
    from datetime import date as date_type

    records = await CheckinRecord.find(
        CheckinRecord.student_id == student_id,
        CheckinRecord.class_id == class_id,
    ).sort(-CheckinRecord.checkin_date).to_list()

    if not records:
        return 0

    dates = sorted({r.checkin_date for r in records}, reverse=True)
    today = date_type.today()

    # Streak must include today or yesterday
    if dates[0] < today - timedelta(days=1):
        return 0

    streak = 1
    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


@router.get("/pages/students/me/badges", name="badges_page")
@webpage.page("student/badges.html")
async def badges_page(
    request: Request,
    user: User = Depends(get_page_user),
):
    badges = await get_student_badges(str(user.id))
    page_ctx = await build_page_context(user)
    return {**page_ctx, "badges": badges}


# ── Teacher badge management page ────────────────────────────────────────────

@router.get("/pages/classes/{class_id}/badges", name="badges_manage_page")
@webpage.page("teacher/badges_manage.html")
async def badges_manage_page(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Fetch all badge definitions for this class with award counts
    badge_defs = await BadgeDefinition.find(
        BadgeDefinition.class_id == class_id,
    ).to_list()

    badges = []
    for b in badge_defs:
        award_count = await BadgeAward.find(
            BadgeAward.badge_id == str(b.id),
            BadgeAward.class_id == class_id,
        ).count()
        badges.append({
            "id": str(b.id),
            "name": b.name,
            "description": b.description,
            "icon": b.icon,
            "trigger_key": b.trigger_key,
            "trigger_rule_id": b.trigger_rule_id,
            "award_count": award_count,
        })

    # Fetch available trigger rules for the dropdown
    rules = await get_rules_for_class(class_id)
    trigger_rules = [
        {
            "id": str(r.id),
            "name": r.name,
            "expression": r.expression,
        }
        for r in rules
        if r.is_active
    ]

    page_ctx = await build_page_context(user)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "badges": badges,
        "trigger_rules": trigger_rules,
    }
