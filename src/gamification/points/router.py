"""Points router."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_TASKS
from core.classes.models import ClassMembership
from core.users.models import User
from gamification.points.service import (
    award_points,
    deduct_points,
    get_balance,
    get_class_balance,
    get_transaction_history,
    revoke_points,
)
from shared.page_context import build_page_context
from shared.webpage import webpage

router = APIRouter(tags=["points"])


class DeductRequest(BaseModel):
    student_id: str
    class_id: str
    amount: int
    reason: str


class RevokeRequest(BaseModel):
    amount: int
    reason: str


class ConfigRequest(BaseModel):
    checkin_points: int = 5
    submission_points: int = 10


@router.post("/api/points/deduct")
async def deduct_student_points(
    body: DeductRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount must be positive",
        )
    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(body.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    tx = await deduct_points(
        student_id=body.student_id,
        class_id=body.class_id,
        amount=body.amount,
        reason=body.reason,
        deducted_by=str(teacher.id),
    )
    return {"deducted": abs(tx.amount), "new_balance": await get_class_balance(body.student_id, body.class_id)}


@router.get("/students/me/points")
async def my_points(user: User = Depends(get_current_user)):
    balance = await get_balance(str(user.id))
    history = await get_transaction_history(str(user.id))
    return {
        "balance": balance,
        "transactions": [
            {
                "amount": t.amount,
                "reason": t.reason,
                "source_event": t.source_event,
                "created_at": t.created_at.isoformat(),
            }
            for t in history
        ],
    }


@router.post("/classes/{class_id}/students/{student_id}/point-revoke")
async def revoke_student_points(
    class_id: str,
    student_id: str,
    body: RevokeRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount must be positive",
        )
    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    tx = await revoke_points(
        student_id=student_id,
        class_id=class_id,
        amount=body.amount,
        reason=body.reason,
        revoked_by=str(teacher.id),
    )
    return {"deducted": abs(tx.amount), "new_balance": await get_class_balance(student_id, class_id)}


@router.patch("/classes/{class_id}/point-config")
async def update_point_config(
    class_id: str,
    body: ConfigRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    from core.classes.models import Class
    from core.classes.service import can_manage_class
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    from gamification.points.models import ClassPointConfig
    existing = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    if existing:
        existing.checkin_points = body.checkin_points
        existing.submission_points = body.submission_points
        await existing.save()
    else:
        config = ClassPointConfig(
            class_id=class_id,
            checkin_points=body.checkin_points,
            submission_points=body.submission_points,
        )
        await config.insert()
    return {"class_id": class_id, "checkin_points": body.checkin_points, "submission_points": body.submission_points}


@router.get("/pages/classes/{class_id}/points", name="points_manage_page")
@webpage.page("teacher/points_manage.html")
async def points_manage_page(
    request: Request,
    class_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    from core.classes.models import Class
    from gamification.points.models import ClassPointConfig

    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    from core.classes.service import can_manage_class
    if not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=403, detail="Permission denied")

    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id,
        ClassMembership.role == "student",
    ).to_list()

    members_data = []
    for m in memberships:
        balance = await get_class_balance(m.user_id, class_id)
        u = await User.get(m.user_id)
        members_data.append({
            "student_id": m.user_id,
            "display_name": u.display_name if u else m.user_id,
            "balance": balance,
        })

    config = await ClassPointConfig.find_one(ClassPointConfig.class_id == class_id)
    config_data = config or ClassPointConfig(class_id=class_id)

    page_ctx = await build_page_context(teacher)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "members": members_data,
        "config": config_data,
    }
