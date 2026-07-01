"""Classes router."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_OWN_CLASS, MANAGE_ALL_CLASSES, READ_CLASS
from core.classes.models import Class, ClassMembership
from core.classes.service import (
    batch_invite_students,
    can_manage_class,
    create_class,
    create_join_request,
    get_class_members,
    get_pending_join_requests,
    get_public_classes,
    join_class_by_code,
    join_class_by_id,
    promote_to_teacher,
    regenerate_invite_code,
    remove_member,
    list_students_for_invite,
    review_join_request,
    search_students_for_invite,
    set_visibility,
)
from core.users.models import IdentityTag, User
from shared.limiter import limiter

router = APIRouter(prefix="/classes", tags=["classes"])

_CAN_CREATE_CLASS = MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES


async def _require_manage(class_id: str, user: User) -> Class:
    """Load class and assert user can manage it; raises 403 if not authorised."""
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return cls


class CreateClassRequest(BaseModel):
    name: str
    description: str = ""
    visibility: str = "public"


class JoinByCodeRequest(BaseModel):
    invite_code: str


class SetVisibilityRequest(BaseModel):
    visibility: str


class BatchInviteRequest(BaseModel):
    user_ids: list[str]


class ReviewJoinRequestBody(BaseModel):
    action: str  # "approve" or "reject"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_class_endpoint(
    body: CreateClassRequest,
    teacher: User = Depends(require_permission(_CAN_CREATE_CLASS)),
):
    cls = await create_class(body.name, body.description, body.visibility, teacher)
    return {"id": str(cls.id), "name": cls.name, "invite_code": cls.invite_code}


@router.get("/public")
async def list_public_classes(_: User = Depends(get_current_user)):
    classes = await get_public_classes()
    return [{"id": str(c.id), "name": c.name, "description": c.description} for c in classes]


@router.post("/join")
@limiter.limit("5/minute")
async def join_by_code(request: Request, body: JoinByCodeRequest, user: User = Depends(get_current_user)):
    """Submit a join request via invite code (requires teacher approval)."""
    if IdentityTag.STUDENT not in user.identity_tags:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can submit join requests")
    config = getattr(request.app.state, "system_config", None)
    cooldown = config.join_request_reject_cooldown_hours if config else 24
    try:
        jr = await create_join_request(user, body.invite_code, cooldown_hours=cooldown)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"class_id": jr.class_id, "message": "Join request submitted, pending teacher review"}


@router.post("/join-request")
@limiter.limit("5/minute")
async def submit_join_request(request: Request, body: JoinByCodeRequest, user: User = Depends(get_current_user)):
    """Submit a join request via invite code (alias endpoint)."""
    if IdentityTag.STUDENT not in user.identity_tags:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can submit join requests")
    config = getattr(request.app.state, "system_config", None)
    cooldown = config.join_request_reject_cooldown_hours if config else 24
    try:
        jr = await create_join_request(user, body.invite_code, cooldown_hours=cooldown)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"class_id": jr.class_id, "message": "Join request submitted, pending teacher review"}


@router.post("/{class_id}/join")
async def join_public_class(class_id: str, user: User = Depends(get_current_user)):
    try:
        m = await join_class_by_id(user, class_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"class_id": m.class_id, "message": "Joined class"}


@router.patch("/{class_id}/visibility")
async def update_visibility(
    class_id: str,
    body: SetVisibilityRequest,
    user: User = Depends(get_current_user),
):
    cls = await _require_manage(class_id, user)
    try:
        cls = await set_visibility(class_id, body.visibility)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": str(cls.id), "visibility": cls.visibility}


@router.get("/{class_id}/members")
async def list_members(class_id: str, user: User = Depends(get_current_user)):
    await _require_manage(class_id, user)
    members = await get_class_members(class_id)
    return [{"user_id": m.user_id, "role": m.role} for m in members]


@router.delete("/{class_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_class_member(
    class_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
):
    await _require_manage(class_id, user)
    await remove_member(class_id, user_id)


@router.patch("/{class_id}/members/{user_id}/promote")
async def promote_member(
    class_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
):
    await _require_manage(class_id, user)
    try:
        m = await promote_to_teacher(class_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"user_id": m.user_id, "role": m.role}


@router.post("/{class_id}/invite-code/regenerate")
async def regen_invite_code(class_id: str, user: User = Depends(get_current_user)):
    await _require_manage(class_id, user)
    try:
        new_code = await regenerate_invite_code(class_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"invite_code": new_code}


@router.get("/{class_id}/invite/search")
async def search_invite_students(
    class_id: str,
    q: str = "",
    type: str = "name",
    user: User = Depends(get_current_user),
):
    """Search for students not yet in this class (by name or admin class_name)."""
    await _require_manage(class_id, user)
    results = await search_students_for_invite(class_id, q=q, search_type=type)
    return results


@router.post("/{class_id}/invite/batch", status_code=status.HTTP_201_CREATED)
async def batch_invite(
    class_id: str,
    body: BatchInviteRequest,
    user: User = Depends(get_current_user),
):
    """Directly add a list of users to the class as students."""
    await _require_manage(class_id, user)
    added = await batch_invite_students(class_id, body.user_ids)
    return {"added": added}


@router.get("/{class_id}/invite/students")
async def list_invite_students(
    class_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    user: User = Depends(get_current_user),
):
    """List students available for invite with pagination."""
    await _require_manage(class_id, user)
    students, total = await list_students_for_invite(class_id, offset=offset, limit=limit)
    return {
        "students": students,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{class_id}/join-requests")
async def list_join_requests(class_id: str, user: User = Depends(get_current_user)):
    """List pending join requests for a class (teacher-only)."""
    await _require_manage(class_id, user)
    requests = await get_pending_join_requests(class_id)
    from core.users.models import User as UserModel
    result = []
    for jr in requests:
        student = await UserModel.get(jr.user_id)
        result.append({
            "id": str(jr.id),
            "user_id": jr.user_id,
            "student_name": student.display_name if student else "Unknown",
            "student_real_name": student.name if student else "",
            "requested_at": jr.requested_at.isoformat(),
            "invite_code_used": jr.invite_code_used,
        })
    return result


@router.patch("/{class_id}/join-requests/{request_id}/review")
async def review_join_request_endpoint(
    class_id: str,
    request_id: str,
    body: ReviewJoinRequestBody,
    user: User = Depends(get_current_user),
):
    """Approve or reject a pending join request (teacher-only)."""
    await _require_manage(class_id, user)
    try:
        jr = await review_join_request(request_id=request_id, action=body.action, reviewer=user, class_id=class_id)
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return {"id": str(jr.id), "status": jr.status}


class DiscordWebhookRequest(BaseModel):
    webhook_url: str


_DISCORD_WEBHOOK_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)


@router.patch("/{class_id}/discord-webhook")
async def update_discord_webhook(
    class_id: str,
    body: DiscordWebhookRequest,
    user: User = Depends(get_current_user),
):
    """Save or clear the Discord Webhook URL for a class (teacher-only)."""
    url = body.webhook_url.strip()
    if url and not any(url.startswith(p) for p in _DISCORD_WEBHOOK_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Discord webhook URL. Must start with https://discord.com/api/webhooks/ or https://discordapp.com/api/webhooks/",
        )
    cls = await _require_manage(class_id, user)
    cls.discord_webhook_url = url or None
    await cls.save()
    return {"id": str(cls.id), "has_discord_webhook": cls.discord_webhook_url is not None}


class DiscordTemplateRequest(BaseModel):
    title_format: str | None = None
    description_template: str | None = None
    footer_text: str | None = None


@router.patch("/{class_id}/discord-template")
async def update_discord_template(
    class_id: str,
    body: DiscordTemplateRequest,
    user: User = Depends(get_current_user),
):
    """Set or update the Discord message template for a class (teacher-only)."""
    from core.classes.models import DiscordTemplate
    cls = await _require_manage(class_id, user)
    current = cls.discord_template or DiscordTemplate()
    if body.title_format is not None:
        current.title_format = body.title_format
    if body.description_template is not None:
        current.description_template = body.description_template
    if body.footer_text is not None:
        current.footer_text = body.footer_text
    cls.discord_template = current
    await cls.save()
    return {
        "id": str(cls.id),
        "discord_template": {
            "title_format": current.title_format,
            "description_template": current.description_template,
            "footer_text": current.footer_text,
        },
    }


@router.patch("/{class_id}/archive")
async def archive_class(class_id: str, user: User = Depends(get_current_user)):
    """Archive a class. Only the class owner or a global class manager can do this."""
    cls = await _require_manage(class_id, user)
    cls.is_archived = True
    await cls.save()
    return {"id": str(cls.id), "is_archived": True}


@router.patch("/{class_id}/unarchive")
async def unarchive_class(class_id: str, user: User = Depends(get_current_user)):
    """Unarchive a class."""
    cls = await _require_manage(class_id, user)
    cls.is_archived = False
    await cls.save()
    return {"id": str(cls.id), "is_archived": False}
