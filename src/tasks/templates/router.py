"""Task templates router."""
import logging
from datetime import date
from typing import Any, Literal, Optional

_DateField = date  # module-level alias — prevents 'date' Pydantic field from shadowing the type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, model_validator

from core.auth.deps import get_current_user
from core.auth.guards import require_permission
from core.auth.permissions import MANAGE_TASKS
from core.users.models import User
from integrations.discord.service import send_task_embed as discord_send_task_embed
from tasks.templates.service import (
    archive_template,
    assign_template_to_date,
    create_template,
    delete_template,
    expand_schedule_rule,
    get_template_for_date,
    unarchive_template,
    update_template,
)

router = APIRouter(tags=["templates"])

logger = logging.getLogger(__name__)


class FieldDef(BaseModel):
    name: str
    field_type: str
    required: bool = False


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    fields: list[FieldDef]


class AssignTemplateRequest(BaseModel):
    template_id: str
    date: date


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    fields: list[FieldDef] | None = None


class ScheduleRuleRequest(BaseModel):
    template_id: str
    schedule_type: Literal["once", "range", "open"]
    start_date: Optional[_DateField] = None
    end_date: Optional[_DateField] = None
    weekdays: list[int] = []
    max_submissions_per_student: int = 0
    date: Optional[_DateField] = None
    sync_discord: bool = False
    dc_title_override: Optional[str] = None
    dc_desc_override: Optional[str] = None
    dc_footer_override: Optional[str] = None

    @model_validator(mode="after")
    def _validate_mode_fields(self):
        """Reject malformed rules before persistence (CWE-20).

        Each schedule_type has required date fields; without this guard a
        malformed rule was persisted and then crashed expand_schedule_rule().
        """
        if self.schedule_type == "once":
            if self.date is None:
                raise ValueError("schedule_type 'once' 需要 'date'")
        elif self.schedule_type == "range":
            if self.start_date is None or self.end_date is None:
                raise ValueError("schedule_type 'range' 需要 'start_date' 與 'end_date'")
            if self.end_date < self.start_date:
                raise ValueError("'end_date' 不可早於 'start_date'")
        elif self.schedule_type == "open":
            if self.start_date is None:
                raise ValueError("schedule_type 'open' 需要 'start_date'")
        if any(d < 0 or d > 6 for d in self.weekdays):
            raise ValueError("'weekdays' 元素須介於 0（週一）與 6（週日）之間")
        return self


async def _require_class_manage(class_id: str, user: User) -> None:
    """Verify user can manage the given class; raises 403/404."""
    from core.classes.models import Class
    from core.classes.service import can_manage_class

    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


@router.post("/classes/{class_id}/templates", status_code=status.HTTP_201_CREATED)
async def create_template_endpoint(
    class_id: str,
    body: CreateTemplateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_class_manage(class_id, teacher)
    try:
        tmpl = await create_template(
            name=body.name,
            description=body.description,
            class_id=class_id,
            fields=[f.model_dump() for f in body.fields],
            owner=teacher,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return {"id": str(tmpl.id), "name": tmpl.name}


@router.post("/classes/{class_id}/schedule-rules", status_code=status.HTTP_201_CREATED)
async def create_schedule_rule(
    class_id: str,
    body: ScheduleRuleRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_class_manage(class_id, teacher)
    from tasks.templates.models import TaskScheduleRule
    rule = TaskScheduleRule(
        template_id=body.template_id,
        class_id=class_id,
        schedule_type=body.schedule_type,
        date=body.date,
        start_date=body.start_date,
        end_date=body.end_date,
        weekdays=body.weekdays,
        max_submissions_per_student=body.max_submissions_per_student,
    )
    await rule.insert()
    assignments = await expand_schedule_rule(rule)

    if body.sync_discord:
        from core.classes.models import Class
        from tasks.templates.models import TaskTemplate
        cls = await Class.get(class_id)
        if cls and cls.discord_webhook_url:
            tmpl = await TaskTemplate.get(body.template_id)
            if tmpl:
                date_str = str(body.date or body.start_date or "")
                # Build class template dict for Discord embed
                class_tmpl = None
                if cls.discord_template:
                    class_tmpl = {
                        "title_format": cls.discord_template.title_format,
                        "description_template": cls.discord_template.description_template,
                        "footer_text": cls.discord_template.footer_text,
                    }
                try:
                    await discord_send_task_embed(
                        webhook_url=cls.discord_webhook_url,
                        task_name=tmpl.name,
                        description=tmpl.description,
                        date=date_str or None,
                        class_template=class_tmpl,
                        class_name=cls.name,
                        title_override=body.dc_title_override,
                        description_override=body.dc_desc_override,
                        footer_override=body.dc_footer_override,
                    )
                except Exception:
                    logger.error("Discord send failed for class %s", class_id)

    return {"assignments_created": len(assignments)}


@router.post("/classes/{class_id}/template-assignments", status_code=status.HTTP_201_CREATED)
async def assign_template(
    class_id: str,
    body: AssignTemplateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_class_manage(class_id, teacher)
    assignment = await assign_template_to_date(body.template_id, class_id, body.date)
    return {"template_id": assignment.template_id, "date": str(assignment.date)}


@router.get("/classes/{class_id}/today-template")
async def today_template(class_id: str, user: User = Depends(get_current_user)):
    from core.auth.permissions import MANAGE_ALL_CLASSES
    from core.classes.models import ClassMembership

    if not (user.permissions & MANAGE_ALL_CLASSES):
        membership = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == str(user.id),
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this class")

    tmpl = await get_template_for_date(class_id, date.today())
    if tmpl is None:
        return {"message": "No task available today"}
    return {
        "id": str(tmpl.id),
        "name": tmpl.name,
        "description": tmpl.description,
        "fields": [f.model_dump() for f in tmpl.fields],
    }


async def _require_template_class(template_id: str, user: User) -> None:
    """Verify user can manage the class owning the template; raises 403/404."""
    from core.classes.models import Class
    from core.classes.service import can_manage_class
    from tasks.templates.models import TaskTemplate as TT

    tmpl = await TT.get(template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    cls = await Class.get(tmpl.class_id)
    if cls is None or not await can_manage_class(user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


@router.patch("/templates/{template_id}")
async def update_template_endpoint(
    template_id: str,
    body: UpdateTemplateRequest,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "fields" in updates:
        updates["fields"] = [f.model_dump() for f in body.fields]
    try:
        tmpl = await update_template(template_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": str(tmpl.id), "name": tmpl.name}


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_endpoint(
    template_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    try:
        await delete_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/templates/{template_id}/archive")
async def archive_template_endpoint(
    template_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    try:
        tmpl = await archive_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": str(tmpl.id), "is_archived": tmpl.is_archived}


@router.patch("/templates/{template_id}/unarchive")
async def unarchive_template_endpoint(
    template_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    try:
        tmpl = await unarchive_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": str(tmpl.id), "is_archived": tmpl.is_archived}


from fastapi import Request
from pages.deps import get_page_user
from shared.page_context import build_page_context
from shared.webpage import webpage


@router.get("/pages/teacher/classes/{class_id}/members", name="class_members_page")
@webpage.page("teacher/class_members.html")
async def class_members_page(
    request: Request,
    class_id: str,
    teacher: User = Depends(get_page_user),
):
    from core.auth.permissions import MANAGE_OWN_CLASS, MANAGE_ALL_CLASSES
    from core.classes.models import Class, ClassMembership
    from core.classes.service import can_manage_class
    from core.users.models import User as UserModel
    from fastapi import HTTPException, status as http_status

    if not (teacher.permissions & (MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES)):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")
    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Class not found")
    if not await can_manage_class(teacher, cls):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

    memberships = await ClassMembership.find(ClassMembership.class_id == class_id).to_list()
    members = []
    for m in memberships:
        u = await UserModel.get(m.user_id)
        members.append({
            "user_id": m.user_id,
            "username": u.username if u else m.user_id,
            "display_name": u.display_name if u else m.user_id,
            "role": m.role,
        })
    page_ctx = await build_page_context(teacher)
    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "invite_code": cls.invite_code,
        "is_archived": cls.is_archived,
        "members": members,
    }


@router.get("/pages/teacher/classes/{class_id}/templates", name="templates_list_page")
@webpage.page("teacher/templates_list.html")
async def templates_list_page(
    request: Request,
    class_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_class_manage(class_id, teacher)
    from tasks.templates.models import TaskTemplate as TT
    templates = await TT.find(TT.class_id == class_id).to_list()
    from core.classes.models import Class
    cls = await Class.get(class_id)
    class_name = cls.name if cls else class_id
    page_ctx = await build_page_context(teacher)
    return {**page_ctx, "class_id": class_id, "class_name": class_name, "templates": templates}


@router.get("/pages/teacher/classes/{class_id}/templates/new", name="template_form_page")
@webpage.page("teacher/template_form.html")
async def template_form_page(
    request: Request,
    class_id: str,
    error: str | None = None,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_class_manage(class_id, teacher)
    page_ctx = await build_page_context(teacher)
    return {**page_ctx, "class_id": class_id, "template": None, "error": error}


@router.get("/pages/teacher/templates/{template_id}/edit", name="template_edit_page")
@webpage.page("teacher/template_form.html")
async def template_edit_page(
    request: Request,
    template_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    from tasks.templates.models import TaskTemplate as TT
    tmpl = await TT.get(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    page_ctx = await build_page_context(teacher)
    return {**page_ctx, "class_id": tmpl.class_id, "template": tmpl, "error": None}


@router.get("/pages/teacher/templates/{template_id}/assign", name="template_assign_page")
@webpage.page("teacher/template_assign.html")
async def template_assign_page(
    request: Request,
    template_id: str,
    teacher: User = Depends(require_permission(MANAGE_TASKS)),
):
    await _require_template_class(template_id, teacher)
    from tasks.templates.models import TaskTemplate as TT
    tmpl = await TT.get(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    from core.classes.models import Class
    cls = await Class.get(tmpl.class_id)
    class_name = cls.name if cls else tmpl.class_id
    has_discord_webhook = bool(cls and cls.discord_webhook_url)
    page_ctx = await build_page_context(teacher)
    return {
        **page_ctx,
        "class_id": tmpl.class_id,
        "class_name": class_name,
        "template": tmpl,
        "has_discord_webhook": has_discord_webhook,
    }
