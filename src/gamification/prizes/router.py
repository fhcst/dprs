"""Prizes router."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_TASKS
from core.classes.models import Class, ClassMembership
from core.classes.service import can_manage_class
from core.users.models import User
from gamification.points.service import get_balance
from gamification.prizes.models import Prize
from gamification.prizes.service import InsufficientPointsError, redeem_prize
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage

router = APIRouter(tags=["prizes"])


class PrizeCreateRequest(BaseModel):
    title: str
    description: str = ""
    prize_type: Literal["online", "physical"] = "online"
    image_url: Optional[str] = None
    point_cost: int = 0
    visible: bool = True


class PrizePatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    prize_type: Optional[Literal["online", "physical"]] = None
    image_url: Optional[str] = None
    point_cost: Optional[int] = None
    visible: Optional[bool] = None


@router.post("/classes/{class_id}/prizes", status_code=status.HTTP_201_CREATED)
async def create_prize(
    class_id: str,
    body: PrizeCreateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Align create with the redeem invariant (point_cost > 0): a non-positive
    # cost would produce a visible-but-never-redeemable prize, since the redeem
    # path rejects point_cost <= 0. Refuse it at the source.
    if body.point_cost <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Point cost must be greater than 0",
        )

    prize = Prize(
        class_id=class_id,
        title=body.title,
        description=body.description,
        prize_type=body.prize_type,
        image_url=body.image_url,
        point_cost=body.point_cost,
        visible=body.visible,
        created_by=str(teacher.id),
    )
    await prize.insert()
    return {"id": str(prize.id), "title": prize.title}


@router.get("/classes/{class_id}/prizes")
async def list_prizes(
    class_id: str,
    user: User = Depends(get_current_user),
):
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    # Class-scoped authorization: managers see all prizes; members see only
    # visible prizes; non-members are refused (was: any authenticated user could
    # enumerate another class's prizes, incl. invisible ones — CWE-200).
    is_manager = await can_manage_class(user, cls)
    if not is_manager:
        membership = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == str(user.id),
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")

    if is_manager:
        prizes = await Prize.find(Prize.class_id == class_id).to_list()
    else:
        prizes = await Prize.find(Prize.class_id == class_id, Prize.visible == True).to_list()  # noqa: E712
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "description": p.description,
            "prize_type": p.prize_type,
            "image_url": p.image_url,
            "point_cost": p.point_cost,
            "visible": p.visible,
        }
        for p in prizes
    ]


@router.patch("/prizes/{prize_id}")
async def update_prize(
    prize_id: str,
    body: PrizePatchRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    prize = await Prize.get(prize_id)
    if prize is None:
        raise HTTPException(status_code=404, detail="Prize not found")
    cls = await Class.get(prize.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Same positive-cost invariant as create: an edit must not be able to push a
    # prize into the unredeemable point_cost <= 0 state.
    if body.point_cost is not None and body.point_cost <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Point cost must be greater than 0",
        )

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(prize, field, value)
    await prize.save()
    return {"id": str(prize.id), "visible": prize.visible}


@router.delete("/prizes/{prize_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prize(
    prize_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    prize = await Prize.get(prize_id)
    if prize is None:
        raise HTTPException(status_code=404, detail="Prize not found")
    cls = await Class.get(prize.class_id)
    if cls is None or not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    await prize.delete()


# ── Student redemption endpoint ──────────────────────────────────────────────

@router.post("/classes/{class_id}/prizes/{prize_id}/redeem", name="redeem_prize")
async def redeem_prize_endpoint(
    class_id: str,
    prize_id: str,
    student: User = Depends(get_current_user),
):
    """Redeem a prize for the authenticated student.

    Guard order (mirrors the badge membership/IDOR pattern — class is always
    derived from the loaded prize, never trusted from the caller):
      1. prize exists                              → else 404
      2. prize.class_id == path class_id           → else 404 (cross-class)
      3. student is a student-role member          → else 403
      4. prize.visible                             → else 400
      5. prize.point_cost > 0                       → else 400 (not redeemable)
      6. balance >= point_cost                     → else 400 (no deduction)

    Membership is checked BEFORE visibility so a non-member always gets a uniform
    403 regardless of the prize's visibility — otherwise the 400 (invisible) vs
    403 (visible) split would leak prize visibility to non-members, defeating the
    cross-class branch's own non-leaking intent.
    """
    prize = await Prize.get(prize_id)
    if prize is None:
        raise HTTPException(status_code=404, detail="Prize not found")
    if prize.class_id != class_id:
        # Cross-class access: do not leak the prize's real class.
        raise HTTPException(status_code=404, detail="Prize not found")

    # Redemption is restricted to *student-role* members (design: 兌換以 student
    # member 為準). Any-role members may still view the page, but only a student
    # membership may spend points here. Checked before the visibility guard so a
    # non-member cannot distinguish a visible from an invisible prize.
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == prize.class_id,
        ClassMembership.user_id == str(student.id),
        ClassMembership.role == "student",
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a class member")

    if not prize.visible:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prize not available")

    # Reject non-positive cost before any balance check: with point_cost <= 0 the
    # `balance < point_cost` guard never trips and the deduction `amount=-point_cost`
    # becomes non-negative, minting points or allowing unlimited free redemptions.
    if prize.point_cost <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prize not redeemable")

    balance = await get_balance(str(student.id))
    if balance < prize.point_cost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient points")

    try:
        _, new_balance = await redeem_prize(str(student.id), prize)
    except InsufficientPointsError:
        # Re-check inside the service lost the race — still no deduction occurred.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient points")

    return {
        "prize_id": str(prize.id),
        "title": prize.title,
        "point_cost": prize.point_cost,
        "new_balance": new_balance,
    }


# ── Student prize page ───────────────────────────────────────────────────────

@router.get("/pages/classes/{class_id}/prizes", name="prizes_page")
@webpage.page("student/prizes.html")
async def prizes_page(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    # Only class members may view the class's prize catalog (parity with the
    # redeem endpoint). Any membership role may view; redemption itself is
    # further restricted to student-role members in the redeem endpoint.
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == str(user.id),
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a class member")

    prizes = await Prize.find(
        Prize.class_id == class_id, Prize.visible == True  # noqa: E712
    ).to_list()
    balance = await get_balance(str(user.id))
    page_ctx = await build_page_context(user)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "balance": balance,
        "prizes": [
            {
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "point_cost": p.point_cost,
            }
            for p in prizes
        ],
    }


# ── Teacher prize management page ────────────────────────────────────────────

@router.get("/pages/classes/{class_id}/prizes/manage", name="prizes_manage_page")
@webpage.page("teacher/prizes_manage.html")
async def prizes_manage_page(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    prizes = await Prize.find(Prize.class_id == class_id).to_list()
    page_ctx = await build_page_context(user)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "prizes": [
            {
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "point_cost": p.point_cost,
                "visible": p.visible,
            }
            for p in prizes
        ],
    }
