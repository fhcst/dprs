"""Check-in router."""
from datetime import date as date_type, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.classes.models import Class
from core.classes.service import can_manage_class
from core.users.models import User
from extensions.deps import get_reward_providers
from extensions.protocols.reward import RewardEvent, RewardEventType
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage
from tasks.checkin.service import (
    MembershipError,
    do_checkin,
    is_checkin_open,
    set_daily_override,
    set_global_config,
)

router = APIRouter(tags=["checkin"])


async def _require_manage(class_id: str, user: User) -> Class:
    """Load class and assert user can manage it; raises 403 if not authorised."""
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return cls


class GlobalConfigRequest(BaseModel):
    active_weekdays: list[int]
    window_start: Optional[str] = None  # "HH:MM"
    window_end: Optional[str] = None


class OverrideRequest(BaseModel):
    date: str  # "YYYY-MM-DD"
    active: bool
    window_start: Optional[str] = None
    window_end: Optional[str] = None


@router.post("/classes/{class_id}/checkin-config")
async def configure_checkin(
    class_id: str,
    body: GlobalConfigRequest,
    user: User = Depends(get_current_user),
):
    await _require_manage(class_id, user)
    from datetime import time as dt_time
    ws = None
    we = None
    if body.window_start:
        h, m = body.window_start.split(":")
        ws = dt_time(int(h), int(m))
    if body.window_end:
        h, m = body.window_end.split(":")
        we = dt_time(int(h), int(m))
    config = await set_global_config(class_id, body.active_weekdays, ws, we)
    return {"class_id": class_id, "active_weekdays": config.active_weekdays}


@router.post("/classes/{class_id}/checkin-overrides")
async def create_override(
    class_id: str,
    body: OverrideRequest,
    user: User = Depends(get_current_user),
):
    await _require_manage(class_id, user)
    from datetime import date, time as dt_time
    target_date = date.fromisoformat(body.date)
    ws = None
    we = None
    if body.window_start:
        h, m = body.window_start.split(":")
        ws = dt_time(int(h), int(m))
    if body.window_end:
        h, m = body.window_end.split(":")
        we = dt_time(int(h), int(m))
    override = await set_daily_override(class_id, target_date, body.active, ws, we)
    return {"date": str(override.date), "active": override.active}


@router.post("/classes/{class_id}/checkin", status_code=status.HTTP_201_CREATED)
async def checkin(class_id: str, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    try:
        record = await do_checkin(user, class_id, now)
    except MembershipError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Trigger RewardProviders
    event = RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(user.id),
        class_id=class_id,
        source_id=str(record.id),
    )
    for provider in get_reward_providers():
        await provider.award(event)

    # Evaluate BadgeTriggers
    from gamification.badges.service import evaluate_triggers_for_event
    await evaluate_triggers_for_event(str(user.id), event, class_id)

    return {"checked_in_at": record.checked_in_at.isoformat()}


@router.post("/classes/{class_id}/checkin/browser")
@webpage.redirect(status_code=302)
async def checkin_browser(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    """Browser form-based check-in with PRG pattern."""
    now = datetime.now(timezone.utc)
    try:
        record = await do_checkin(user, class_id, now)
    except MembershipError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
    except ValueError as e:
        error_msg = str(e)
        dashboard_base = str(request.url_for("dashboard_page"))
        # "Already checked in" is not an error — redirect silently to dashboard
        if "already checked in" in error_msg.lower():
            return (dashboard_base, 302)
        # Other errors (window closed, etc.) → redirect with error param
        dashboard_url = request.url_for("dashboard_page").include_query_params(error=error_msg)
        return (str(dashboard_url), 302)

    # Trigger RewardProviders
    event = RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(user.id),
        class_id=class_id,
        source_id=str(record.id),
    )
    for provider in get_reward_providers():
        await provider.award(event)

    from gamification.badges.service import evaluate_triggers_for_event
    await evaluate_triggers_for_event(str(user.id), event, class_id)

    return str(request.url_for("dashboard_page"))


@router.get("/pages/teacher/classes/{class_id}/checkin-config", name="checkin_config_page")
@webpage.page("teacher/checkin_config.html")
async def checkin_config_page(
    request: Request,
    class_id: str,
    teacher: User = Depends(get_page_user),
    success: Optional[str] = None,
):
    """Teacher page to view and update checkin schedule and single-day overrides."""
    from tasks.checkin.models import CheckinConfig

    await _require_manage(class_id, teacher)

    config = await CheckinConfig.find_one(CheckinConfig.class_id == class_id)
    if config:
        config_data = {
            "active_weekdays": config.active_weekdays,
            "window_start": config.window_start,
            "window_end": config.window_end,
        }
    else:
        config_data = {
            "active_weekdays": list(range(7)),  # default: all days
            "window_start": None,
            "window_end": None,
        }

    page_ctx = await build_page_context(teacher)
    return {
        **page_ctx,
        "class_id": class_id,
        "config": config_data,
        "success": success,
    }


class AttendanceCorrectionRequest(BaseModel):
    student_id: str
    date: str  # "YYYY-MM-DD"
    status: Literal["late", "absent"]
    partial_points: int | None = None  # required when status=="late"


@router.get("/pages/teacher/classes/{class_id}/attendance", name="attendance_manage_page")
@webpage.page("teacher/attendance_manage.html")
async def attendance_manage_page(
    request: Request,
    class_id: str,
    target_date: str | None = None,
    teacher: User = Depends(get_page_user),
):
    """Teacher views daily attendance list for a class (Teacher views daily attendance list)."""
    from core.auth.permissions import MANAGE_OWN_CLASS, MANAGE_ALL_CLASSES
    if not (teacher.permissions & (MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES)):
        raise HTTPException(status_code=403, detail="Permission denied")

    from core.classes.models import Class, ClassMembership
    from core.users.models import User as UserModel
    from tasks.checkin.models import CheckinRecord, AttendanceCorrection
    from gamification.points.models import ClassPointConfig

    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    from core.classes.service import can_manage_class
    if not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Default to today (Page defaults to today's date)
    if target_date:
        selected_date = date_type.fromisoformat(target_date)
    else:
        selected_date = date_type.today()

    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    checkin_points = config.checkin_points if config else 5

    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id,
        ClassMembership.role == "student",
    ).to_list()

    # Load corrections for this date (AttendanceCorrection reflects current status on attendance page)
    corrections: dict[str, AttendanceCorrection] = {}
    for corr in await AttendanceCorrection.find(
        AttendanceCorrection.class_id == class_id,
        AttendanceCorrection.date == selected_date,
    ).to_list():
        corrections[corr.student_id] = corr

    students = []
    for m in memberships:
        u = await UserModel.get(m.user_id)
        if not u:
            continue
        has_checkin = await CheckinRecord.find_one(
            CheckinRecord.student_id == m.user_id,
            CheckinRecord.class_id == class_id,
            CheckinRecord.checkin_date == selected_date,
        ) is not None
        correction = corrections.get(m.user_id)
        students.append({
            "student_id": m.user_id,
            "display_name": u.display_name,
            "has_checkin": has_checkin,
            "correction": correction,
        })

    page_ctx = await build_page_context(teacher)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "selected_date": selected_date.isoformat(),
        "students": students,
        "checkin_points": checkin_points,
    }


@router.post("/api/classes/{class_id}/attendance/correct")
async def correct_attendance(
    class_id: str,
    body: AttendanceCorrectionRequest,
    teacher: User = Depends(get_current_user),
):
    """Teacher corrects attendance: late (partial points) or absent (revoke points).

    Implements: Teacher marks absent student as late /
                Teacher revokes check-in for student who was actually absent /
                Existing correction is overwritten /
                Partial points must be between 1 and checkin_points
    """
    await _require_manage(class_id, teacher)
    from tasks.checkin.models import CheckinRecord, AttendanceCorrection
    from gamification.points.models import ClassPointConfig
    from gamification.points.service import award_points, deduct_points

    target_date = date_type.fromisoformat(body.date)

    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    checkin_pts = config.checkin_points if config else 5

    # Validate partial_points range for "late" status
    if body.status == "late":
        if body.partial_points is None or not (1 <= body.partial_points <= checkin_pts):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"partial_points must be between 1 and {checkin_pts}",
            )

    # Upsert AttendanceCorrection (Existing correction is overwritten)
    existing_correction = await AttendanceCorrection.find_one(
        AttendanceCorrection.class_id == class_id,
        AttendanceCorrection.student_id == body.student_id,
        AttendanceCorrection.date == target_date,
    )
    if existing_correction:
        existing_correction.status = body.status
        existing_correction.partial_points = body.partial_points
        existing_correction.created_by = str(teacher.id)
        await existing_correction.save()
        correction = existing_correction
    else:
        correction = AttendanceCorrection(
            class_id=class_id,
            student_id=body.student_id,
            date=target_date,
            status=body.status,
            partial_points=body.partial_points,
            created_by=str(teacher.id),
        )
        await correction.insert()

    # Apply point adjustment
    if body.status == "late":
        # Award partial points (Teacher marks absent student as late)
        await award_points(
            student_id=body.student_id,
            class_id=class_id,
            amount=body.partial_points,
            source_event="checkin_manual_late",
            source_id=str(correction.id),
            created_by=str(teacher.id),
        )
    else:
        # Revoke checkin points (Teacher revokes check-in for student who was actually absent)
        # Only revoke if student actually had a checkin record (and thus received points)
        has_checkin = await CheckinRecord.find_one(
            CheckinRecord.student_id == body.student_id,
            CheckinRecord.class_id == class_id,
            CheckinRecord.checkin_date == target_date,
        )
        if has_checkin:
            await deduct_points(
                student_id=body.student_id,
                class_id=class_id,
                amount=checkin_pts,
                reason="checkin_manual_revoke",
                deducted_by=str(teacher.id),
            )

    return {"status": body.status, "correction_id": str(correction.id)}


@router.get("/classes/{class_id}/checkin-status")
async def checkin_status(class_id: str, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    result = await is_checkin_open(class_id, now)

    # Check if student already checked in today
    from tasks.checkin.models import CheckinRecord
    existing = await CheckinRecord.find_one(
        CheckinRecord.student_id == str(user.id),
        CheckinRecord.class_id == class_id,
        CheckinRecord.checkin_date == now.date(),
    )

    return {
        "is_open": result.is_open,
        "closes_at": result.closes_at.isoformat() if result.closes_at else None,
        "already_checked_in": existing is not None,
        "reason": result.reason,
    }
