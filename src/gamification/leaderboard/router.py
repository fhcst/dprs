"""Leaderboard router."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth.deps import get_current_user
from core.auth.permissions import MANAGE_ALL_CLASSES, MANAGE_OWN_CLASS as MANAGE_CLASS
from core.classes.models import Class, ClassMembership
from core.users.models import User
from gamification.points.service import get_class_balance
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage

router = APIRouter(tags=["leaderboard"])


async def _build_class_leaderboard(class_id: str) -> list[dict]:
    """Return ranked list of students by point balance."""
    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id,
        ClassMembership.role == "student",
    ).to_list()

    entries = []
    for m in memberships:
        user = await User.get(m.user_id)
        balance = await get_class_balance(m.user_id, class_id)
        entries.append({
            "student_id": m.user_id,
            "display_name": user.display_name if user else m.user_id,
            "points": balance,
        })

    entries.sort(key=lambda e: e["points"], reverse=True)

    # Assign ranks — tied students share the same rank
    rank = 1
    for i, entry in enumerate(entries):
        if i > 0 and entries[i]["points"] < entries[i - 1]["points"]:
            rank = i + 1
        entry["rank"] = rank

    return entries


@router.get("/classes/{class_id}/leaderboard")
async def class_leaderboard(
    class_id: str,
    user: User = Depends(get_current_user),
):
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    if not (user.permissions & MANAGE_ALL_CLASSES):
        membership = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == str(user.id),
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")

    if not (user.permissions & MANAGE_CLASS) and not cls.leaderboard_enabled:
        return {"visible": False, "message": "Leaderboard is not enabled for this class"}

    return {"visible": True, "leaderboard": await _build_class_leaderboard(class_id)}


@router.get("/leaderboard")
async def cross_class_leaderboard(user: User = Depends(get_current_user)):
    """Aggregate leaderboard across public + leaderboard-enabled classes."""
    classes = await Class.find(
        Class.visibility == "public",
        Class.leaderboard_enabled == True,  # noqa: E712
    ).to_list()

    combined: dict[str, dict] = {}
    for cls in classes:
        entries = await _build_class_leaderboard(str(cls.id))
        for entry in entries:
            sid = entry["student_id"]
            if sid not in combined:
                combined[sid] = {"student_id": sid, "display_name": entry["display_name"], "points": 0}
            combined[sid]["points"] += entry["points"]

    ranked = sorted(combined.values(), key=lambda e: e["points"], reverse=True)
    rank = 1
    for i, entry in enumerate(ranked):
        if i > 0 and ranked[i]["points"] < ranked[i - 1]["points"]:
            rank = i + 1
        entry["rank"] = rank

    return {"leaderboard": ranked}


@router.get("/pages/classes/{class_id}/leaderboard", name="leaderboard_page")
@webpage.page("community/leaderboard.html")
async def leaderboard_page(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    if not (user.permissions & MANAGE_ALL_CLASSES):
        membership = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == str(user.id),
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")

    visible = bool(user.permissions & MANAGE_CLASS) or cls.leaderboard_enabled
    entries = await _build_class_leaderboard(class_id) if visible else []

    from gamification.badges.models import BadgeAward
    from gamification.badges.service import active_awards_query
    for entry in entries:
        count = await active_awards_query(BadgeAward.student_id == entry["student_id"]).count()
        entry["badge_count"] = count

    page_ctx = await build_page_context(user)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "visible": visible,
        "leaderboard": entries,
    }
