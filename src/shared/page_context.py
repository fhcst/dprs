"""Shared page context dependency for sidebar variables."""
from fastapi import Depends, Request

from core.auth.permissions import (
    MANAGE_ALL_CLASSES,
    MANAGE_OWN_CLASS,
    MANAGE_TASKS,
    MANAGE_USERS,
    WRITE_SYSTEM,
)
from core.classes.models import Class, ClassMembership
from core.users.models import IdentityTag, User
from pages.deps import get_page_user


async def build_page_context(current_user: User) -> dict:
    """Compute sidebar context variables for the given user.

    Returns a dict containing permission flags and the user's non-archived
    class list, suitable for merging into any template context.
    """
    can_manage_class = bool(
        current_user.permissions & (MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES)
    )

    memberships = await ClassMembership.find(
        ClassMembership.user_id == str(current_user.id)
    ).to_list()

    classes = []
    for m in memberships:
        cls = await Class.get(m.class_id)
        if cls and not cls.is_archived:
            classes.append({"class_id": m.class_id, "class_name": cls.name})

    return {
        "current_user": current_user,
        "can_manage_class": can_manage_class,
        "can_manage_all_classes": bool(current_user.permissions & MANAGE_ALL_CLASSES),
        "can_manage_tasks": bool(current_user.permissions & MANAGE_TASKS),
        "can_manage_users": bool(current_user.permissions & MANAGE_USERS),
        "is_sys_admin": bool(current_user.permissions & WRITE_SYSTEM),
        "is_student": IdentityTag.STUDENT in current_user.identity_tags,
        "classes": classes,
    }


async def get_page_context(
    request: Request,
    current_user: User = Depends(get_page_user),
) -> dict:
    """FastAPI dependency that returns the shared page context."""
    return await build_page_context(current_user)
