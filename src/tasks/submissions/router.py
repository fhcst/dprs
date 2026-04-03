"""Task submissions router."""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_TASKS
from core.users.models import User
from extensions.deps import get_reward_providers, get_submission_validators
from extensions.protocols.reward import RewardEvent, RewardEventType
from extensions.protocols.validator import ValidationResult
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage
from tasks.submissions.models import TaskSubmission
from tasks.submissions.service import (
    MembershipError,
    get_class_submissions_for_date,
    get_student_submissions,
    submit_task,
)
from tasks.templates.models import TaskTemplate

router = APIRouter(tags=["submissions"])


async def _student_sidebar_classes(user_id: str) -> list[dict]:
    """Return the list of non-archived classes a student belongs to (for sidebar)."""
    from core.classes.models import Class, ClassMembership
    memberships = await ClassMembership.find(ClassMembership.user_id == user_id).to_list()
    result = []
    for m in memberships:
        c = await Class.get(m.class_id)
        if c and not c.is_archived:
            result.append({"class_id": m.class_id, "class_name": c.name})
    return result


class SubmitRequest(BaseModel):
    field_values: dict[str, Any]
    submission_date: date | None = None


class CommentRequest(BaseModel):
    comment: str


@router.post("/classes/{class_id}/submissions", status_code=status.HTTP_201_CREATED)
async def submit_task_endpoint(
    class_id: str,
    body: SubmitRequest,
    user: User = Depends(get_current_user),
):
    # Get today's template for this class
    target_date = body.submission_date or date.today()
    from tasks.templates.service import get_template_for_date
    template = await get_template_for_date(class_id, target_date)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No task template assigned for today",
        )

    # Run SubmissionValidators
    validators = get_submission_validators()
    for validator in validators:
        result: ValidationResult = await validator.validate(body.field_values, template)
        if not result.valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.error_message,
            )

    try:
        submission = await submit_task(
            template=template,
            class_id=class_id,
            student=user,
            submission_date=target_date,
            field_values=body.field_values,
        )
    except MembershipError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Trigger RewardProviders
    event = RewardEvent(
        event_type=RewardEventType.SUBMISSION,
        student_id=str(user.id),
        class_id=class_id,
        source_id=str(submission.id),
    )
    for provider in get_reward_providers():
        await provider.award(event)

    # Evaluate BadgeTriggers
    from gamification.badges.service import evaluate_triggers_for_event
    await evaluate_triggers_for_event(str(user.id), event, class_id)

    # Compute points earned in this submission
    from gamification.points.models import ClassPointConfig
    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    points_earned = config.submission_points if config else 0

    return {"id": str(submission.id), "date": str(submission.date), "points_earned": points_earned}


@router.post("/api/submissions/{submission_id}/comment")
async def add_submission_comment(
    submission_id: str,
    body: CommentRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    from datetime import datetime, timezone
    sub = await TaskSubmission.get(submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(sub.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    sub.teacher_comment = body.comment
    sub.reviewed_at = datetime.now(timezone.utc)
    await sub.save()
    return {"id": str(sub.id), "teacher_comment": sub.teacher_comment}


@router.get("/students/me/submissions")
async def my_submissions(user: User = Depends(get_current_user)):
    subs = await get_student_submissions(str(user.id))
    return [
        {
            "id": str(s.id),
            "date": str(s.date),
            "template_name": s.template_snapshot.get("name"),
            "field_values": s.field_values,
        }
        for s in subs
    ]


@router.get("/classes/{class_id}/submissions")
async def class_submissions(
    class_id: str,
    date_param: date | None = None,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    target = date_param or date.today()
    subs = await get_class_submissions_for_date(class_id, target)
    return [
        {
            "id": str(s.id),
            "student_id": s.student_id,
            "date": str(s.date),
            "field_values": s.field_values,
        }
        for s in subs
    ]

@router.get("/pages/teacher/class/{class_id}/submissions", name="submission_review_page")
@webpage.page("teacher/submission_review.html")
async def submission_review_page(
    request: Request,
    class_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    from core.classes.models import Class, ClassMembership
    from core.users.models import User as UserModel

    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    all_subs = await TaskSubmission.find(
        TaskSubmission.class_id == class_id
    ).sort(-TaskSubmission.submitted_at).to_list()

    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id,
        ClassMembership.role == "student",
    ).to_list()

    student_map: dict[str, str] = {}
    for m in memberships:
        u = await UserModel.get(m.user_id)
        if u:
            student_map[m.user_id] = u.display_name

    grouped: dict[str, dict] = {}
    for sub in all_subs:
        sid = sub.student_id
        if sid not in grouped:
            grouped[sid] = {
                "student_id": sid,
                "display_name": student_map.get(sid, sid),
                "submissions": [],
            }
        grouped[sid]["submissions"].append(sub)

    page_ctx = await build_page_context(teacher)
    return {**page_ctx, "class_id": class_id, "class_name": cls.name, "students": list(grouped.values())}


class RejectRequest(BaseModel):
    rejection_reason: str
    resubmit_deadline: str | None = None  # ISO 8601 datetime string, e.g. "2026-03-29T23:59:00Z"


@router.post("/api/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    """Approve a submission. Re-awards points if previously rejected.

    Implements: Teacher approves a task submission /
                Teacher approves a previously rejected submission
    """
    from gamification.points.models import ClassPointConfig
    from gamification.points.service import award_points
    from community.feed.models import FeedPost

    sub = await TaskSubmission.get(submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(sub.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    was_rejected = sub.status == "rejected"
    sub.status = "approved"
    await sub.save()

    if was_rejected:
        config = await ClassPointConfig.find_one(ClassPointConfig.class_id == sub.class_id)
        pts = config.submission_points if config else 0
        await award_points(
            student_id=sub.student_id,
            class_id=sub.class_id,
            amount=pts,
            source_event="submission_reapproved",
            source_id=str(sub.id),
            created_by=str(teacher.id),
        )

    await FeedPost(
        submission_id=str(sub.id),
        student_id=sub.student_id,
        class_id=sub.class_id,
        event_type="submission_approved",
    ).insert()

    return {"status": "approved", "submission_id": str(sub.id)}


@router.post("/api/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    body: RejectRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    """Reject a submission with a reason. Revokes submission points.

    Implements: Teacher rejects a task submission /
                Rejection without reason is rejected
    """
    if not body.rejection_reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="rejection_reason is required",
        )

    from datetime import datetime, timezone as tz
    from gamification.points.models import ClassPointConfig
    from gamification.points.service import award_points
    from community.feed.models import FeedPost

    sub = await TaskSubmission.get(submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(sub.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    sub.status = "rejected"
    sub.rejection_reason = body.rejection_reason.strip()
    if body.resubmit_deadline:
        sub.resubmit_deadline = datetime.fromisoformat(body.resubmit_deadline.replace("Z", "+00:00"))
    await sub.save()

    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == sub.class_id)
    pts = config.submission_points if config else 0
    await award_points(
        student_id=sub.student_id,
        class_id=sub.class_id,
        amount=-pts,
        source_event="submission_rejected",
        source_id=str(sub.id),
        created_by=str(teacher.id),
    )

    await FeedPost(
        submission_id=str(sub.id),
        student_id=sub.student_id,
        class_id=sub.class_id,
        event_type="submission_rejected",
    ).insert()

    return {"status": "rejected", "submission_id": str(sub.id)}


@router.get("/pages/student/submissions/{submission_id}/rejection", name="submission_rejection_page")
@webpage.page("student/submission_rejection.html")
async def submission_rejection_page(
    request: Request,
    submission_id: str,
    current_user: User = Depends(get_page_user),
):
    """Student views rejection detail for their own rejected submission.

    Implements: Student views rejection detail page /
                Non-owner cannot access rejection detail
    """
    sub = await TaskSubmission.get(submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if sub.student_id != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    sidebar_classes = await _student_sidebar_classes(str(current_user.id))
    return {
        "current_user": current_user,
        "submission": sub,
        "classes": sidebar_classes,
        "can_manage_class": False,
        "can_manage_all_classes": False,
        "can_manage_tasks": False,
        "can_manage_users": False,
        "is_sys_admin": False,
    }


@router.get("/pages/student/history", name="learning_history_page")
@webpage.page("student/learning_history.html")
async def learning_history_page(
    request: Request,
    current_user: User = Depends(get_page_user),
):
    subs = await TaskSubmission.find(
        TaskSubmission.student_id == str(current_user.id)
    ).sort(-TaskSubmission.submitted_at).limit(50).to_list()

    sidebar_classes = await _student_sidebar_classes(str(current_user.id))
    return {
        "current_user": current_user,
        "submissions": subs,
        "can_manage_tasks": False,
        "can_manage_class": False,
        "can_manage_all_classes": False,
        "can_manage_users": False,
        "is_sys_admin": False,
        "classes": sidebar_classes,
    }


@router.get("/pages/student/classes/{class_id}/history", name="class_history_page")
@webpage.page("student/class_history.html")
async def class_history_page(
    request: Request,
    class_id: str,
    current_user: User = Depends(get_page_user),
):
    from core.classes.models import Class, ClassMembership

    # Verify membership
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == str(current_user.id),
    )
    if not membership:
        raise HTTPException(status_code=403, detail="非此班級成員")

    cls = await Class.get(class_id)
    class_name = cls.name if cls else class_id

    subs = await TaskSubmission.find(
        TaskSubmission.class_id == class_id,
        TaskSubmission.student_id == str(current_user.id),
    ).sort(-TaskSubmission.submitted_at).limit(100).to_list()

    sidebar_classes = await _student_sidebar_classes(str(current_user.id))
    return {
        "current_user": current_user,
        "class_id": class_id,
        "class_name": class_name,
        "submissions": subs,
        "can_manage_tasks": False,
        "can_manage_class": False,
        "can_manage_all_classes": False,
        "can_manage_users": False,
        "is_sys_admin": False,
        "classes": sidebar_classes,
    }


@router.get("/pages/student/classes/{class_id}/submit", name="submit_task_page")
@webpage.page("student/submit_task.html")
async def submit_task_page(
    request: Request,
    class_id: str,
    error: str | None = None,
    success: int | None = None,
    points: int | None = None,
    current_user: User = Depends(get_page_user),
):
    from core.classes.models import ClassMembership
    from tasks.templates.service import get_template_for_date

    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == str(current_user.id),
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="非此班級成員")

    today_template = await get_template_for_date(class_id, date.today())
    if today_template is None:
        return {"current_user": current_user, "class_id": class_id, "template": None, "error": "今日無任務模板", "success": None, "points_earned": None, "rejected_submission": None}

    # Check for a rejected submission with a valid resubmit deadline
    rejected_submission = await TaskSubmission.find_one(
        TaskSubmission.template_id == str(today_template.id),
        TaskSubmission.student_id == str(current_user.id),
        TaskSubmission.class_id == class_id,
        TaskSubmission.status == "rejected",
    )
    return {"current_user": current_user, "class_id": class_id, "template": today_template, "error": error, "success": bool(success), "points_earned": points, "rejected_submission": rejected_submission}


@router.post("/classes/{class_id}/submit")
@webpage.redirect(status_code=302)
async def submit_task_form(
    request: Request,
    class_id: str,
    current_user: User = Depends(get_page_user),
):
    from tasks.templates.service import get_template_for_date

    form_data = await request.form()
    field_values = dict(form_data)

    today = date.today()
    template = await get_template_for_date(class_id, today)
    if template is None:
        error_url = request.url_for("submit_task_page", class_id=class_id).include_query_params(
            error="今日無任務模板"
        )
        return (str(error_url), 302)

    validators = get_submission_validators()
    for validator in validators:
        result: ValidationResult = await validator.validate(field_values, template)
        if not result.valid:
            error_url = request.url_for("submit_task_page", class_id=class_id).include_query_params(
                error=result.error_message
            )
            return (str(error_url), 302)

    try:
        submission = await submit_task(
            template=template,
            class_id=class_id,
            student=current_user,
            submission_date=today,
            field_values=field_values,
        )
    except ValueError as e:
        error_url = request.url_for("submit_task_page", class_id=class_id).include_query_params(
            error=str(e)
        )
        return (str(error_url), 302)

    event = RewardEvent(
        event_type=RewardEventType.SUBMISSION,
        student_id=str(current_user.id),
        class_id=class_id,
        source_id=str(submission.id),
    )
    for provider in get_reward_providers():
        await provider.award(event)

    from gamification.badges.service import evaluate_triggers_for_event
    await evaluate_triggers_for_event(str(current_user.id), event, class_id)

    from gamification.points.models import ClassPointConfig
    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    points_earned = config.submission_points if config else 0

    success_url = request.url_for("submit_task_page", class_id=class_id).include_query_params(
        success=1, points=points_earned
    )
    return (str(success_url), 302)
