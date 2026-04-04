"""Trigger rules router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_OWN_CLASS
from core.classes.models import Class
from core.classes.service import can_manage_class
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage
from core.users.models import User
from gamification.triggers.models import TriggerRule
from gamification.triggers.service import (
    create_trigger_rule,
    delete_trigger_rule,
    get_rule_with_badge_count,
    get_rules_for_class,
    update_trigger_rule,
)

router = APIRouter(tags=["trigger-rules"])


class TriggerRuleCreateRequest(BaseModel):
    name: str
    expression: str


class TriggerRuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    expression: Optional[str] = None
    is_active: Optional[bool] = None


async def _require_class_manage(class_id: str, user: User) -> Class:
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
        )
    return cls


@router.post(
    "/classes/{class_id}/trigger-rules", status_code=status.HTTP_201_CREATED
)
async def create_rule(
    class_id: str,
    body: TriggerRuleCreateRequest,
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    await _require_class_manage(class_id, user)
    try:
        rule = await create_trigger_rule(
            class_id=class_id,
            name=body.name,
            expression=body.expression,
            created_by=str(user.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return {"id": str(rule.id), "name": rule.name}


@router.get("/classes/{class_id}/trigger-rules")
async def list_rules(
    class_id: str,
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    await _require_class_manage(class_id, user)
    rules = await get_rules_for_class(class_id)
    result = []
    for rule in rules:
        data = await get_rule_with_badge_count(rule)
        result.append({
            "id": str(data["rule"].id),
            "name": data["rule"].name,
            "expression": data["rule"].expression,
            "is_active": data["rule"].is_active,
            "bound_badge_count": data["bound_badge_count"],
            "created_at": data["rule"].created_at.isoformat(),
        })
    return result


@router.get("/classes/{class_id}/trigger-rules/{rule_id}")
async def get_rule(
    class_id: str,
    rule_id: str,
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    await _require_class_manage(class_id, user)
    rule = await TriggerRule.get(rule_id)
    if rule is None or rule.class_id != class_id:
        raise HTTPException(status_code=404, detail="Trigger rule not found")
    data = await get_rule_with_badge_count(rule)
    return {
        "id": str(rule.id),
        "name": rule.name,
        "expression": rule.expression,
        "is_active": rule.is_active,
        "bound_badge_count": data["bound_badge_count"],
        "created_by": rule.created_by,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


@router.put("/classes/{class_id}/trigger-rules/{rule_id}")
async def update_rule(
    class_id: str,
    rule_id: str,
    body: TriggerRuleUpdateRequest,
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    await _require_class_manage(class_id, user)
    rule = await TriggerRule.get(rule_id)
    if rule is None or rule.class_id != class_id:
        raise HTTPException(status_code=404, detail="Trigger rule not found")

    try:
        rule = await update_trigger_rule(
            rule,
            name=body.name,
            expression=body.expression,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return {"id": str(rule.id), "name": rule.name, "updated": True}


@router.delete(
    "/classes/{class_id}/trigger-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rule(
    class_id: str,
    rule_id: str,
    user: User = Depends(require_permission(MANAGE_OWN_CLASS)),
):
    await _require_class_manage(class_id, user)
    rule = await TriggerRule.get(rule_id)
    if rule is None or rule.class_id != class_id:
        raise HTTPException(status_code=404, detail="Trigger rule not found")

    try:
        await delete_trigger_rule(rule)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )


# ── Page route ───────────────────────────────────────────────────────────────

@router.get("/pages/classes/{class_id}/trigger-rules", name="trigger_rules_page")
@webpage.page("teacher/trigger-rules.html")
async def trigger_rules_page(
    request: Request,
    class_id: str,
    user: User = Depends(get_page_user),
):
    cls = await Class.get(class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    rules = await get_rules_for_class(class_id)
    rule_list = []
    for rule in rules:
        data = await get_rule_with_badge_count(rule)
        rule_list.append({
            "id": str(data["rule"].id),
            "name": data["rule"].name,
            "expression": data["rule"].expression,
            "is_active": data["rule"].is_active,
            "bound_badge_count": data["bound_badge_count"],
        })

    page_ctx = await build_page_context(user)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "rules": rule_list,
    }
