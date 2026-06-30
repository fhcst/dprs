"""Pages router — login, logout redirect, dashboard, and admin panel."""
import os
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.users.models import User
from pages.deps import get_page_user
from shared.limiter import limiter
from shared.page_context import build_page_context, get_page_context
from shared.webpage import webpage

router = APIRouter(prefix="/pages", tags=["pages"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = 60 * 60 * 24  # 24h


def _is_production() -> bool:
    """Return True only when FASTAPI_APP_ENVIRONMENT is explicitly 'production'.

    Read at call time (not module load time) so tests can monkeypatch os.environ.
    Defaults to False to avoid breaking HTTP localhost development.
    """
    return os.getenv("FASTAPI_APP_ENVIRONMENT", "development") == "production"


def _is_safe_next(next_value: str | None) -> bool:
    """Return True only for a single same-origin relative-path `next` (fail-closed).

    Two-stage validation that closes open-redirect bypasses:

    1. Reject outright any value whose **path/authority portion** (everything before
       the first ``?`` or ``#``) contains a backslash (``\\``), begins with ``//``, or
       contains a colon (``:``); reject any value containing an ASCII control character.
    2. Require a single leading ``/`` and, via ``urlsplit``, an empty ``scheme`` and
       ``netloc``.

    Stage 1's authority checks deliberately ignore the query/fragment: a colon (or
    other reserved char) in a query value — ISO timestamps, ``?from=10:30``, ratios —
    is harmless data that stays on our own origin, so it must round-trip rather than be
    silently dropped. Only the path/authority portion can carry an off-origin vector.

    Stage 1 is still mandatory: an empty ``urlsplit(next).netloc`` is NOT sufficient on
    its own, because e.g. ``/\\evil.com`` yields an empty netloc yet a browser normalises
    ``\\`` to ``/`` into a protocol-relative (off-origin) redirect.
    """
    if not next_value:
        return False
    # Stage 1 — reject dangerous vectors before trusting the parse. Apply the
    # authority checks only to the path portion so legitimate query strings that
    # contain ':'/'\\'/'//' (e.g. ?ts=2026-06-28T12:00:00) still round-trip.
    path_part = next_value.split("?", 1)[0].split("#", 1)[0]
    if "\\" in path_part or path_part.startswith("//") or ":" in path_part:
        return False
    if any(ord(ch) < 0x20 for ch in next_value):
        return False
    # Stage 2 — require a single same-origin relative path.
    if not next_value.startswith("/"):
        return False
    split = urlsplit(next_value)
    return not split.scheme and not split.netloc


@router.get("/login", name="login_page")
@webpage.page("login.html")
async def login_page(request: Request, error: str | None = None, next: str | None = None):
    return {"error": error, "next": next}


@router.post("/login")
@limiter.limit("10/minute")
@webpage.redirect(status_code=302)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(default=None),
):
    from extensions.protocols import AuthProvider
    from extensions.registry import registry
    from core.auth.jwt import create_access_token

    # Validate next URL to prevent open redirect (single same-origin relative path only)
    safe_next = next if _is_safe_next(next) else None

    try:
        provider: AuthProvider = registry.get(AuthProvider, "local")
        user = await provider.authenticate({"username": username, "password": password})
    except Exception:
        error_url = request.url_for("login_page").include_query_params(error="帳號或密碼錯誤")
        return (str(error_url), 302)

    token = create_access_token(user_id=str(user.id), permissions=user.permissions)
    redirect_url = safe_next or str(request.url_for("dashboard_page"))
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        secure=_is_production(),
    )
    return response


@router.get("/dashboard", name="dashboard_page")
@webpage.page("student/dashboard.html")
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_page_user),
    create_class: int = 0,
):
    from datetime import date, datetime, timedelta, timezone

    from core.classes.models import Class, ClassMembership
    from tasks.checkin.models import CheckinRecord
    from tasks.checkin.service import is_checkin_open
    from tasks.templates.service import get_template_for_date

    memberships = await ClassMembership.find(
        ClassMembership.user_id == str(current_user.id)
    ).to_list()

    now = datetime.now(timezone.utc)
    today = date.today()

    page_ctx = await build_page_context(current_user)

    classes = []
    for m in memberships:
        cls = await Class.get(m.class_id)
        if cls is None:
            continue
        # Students don't see archived classes; managers/teachers do
        if cls.is_archived and not page_ctx["can_manage_class"]:
            continue

        checkin_result = await is_checkin_open(m.class_id, now)
        existing_checkin = await CheckinRecord.find_one(
            CheckinRecord.student_id == str(current_user.id),
            CheckinRecord.class_id == m.class_id,
            CheckinRecord.checkin_date == today,
        )
        today_template = await get_template_for_date(m.class_id, today)
        member_count = await ClassMembership.find(
            ClassMembership.class_id == m.class_id
        ).count()

        from core.users.models import User as UserModel
        try:
            owner = await UserModel.get(cls.owner_id)
            owner_display_name = owner.display_name if owner else ""
        except Exception:
            owner_display_name = ""

        # Today's submission status for this student in this class
        submitted_today = False
        submission_status = None
        submission_id = None
        if today_template:
            from tasks.submissions.models import TaskSubmission
            sub = await TaskSubmission.find_one(
                TaskSubmission.template_id == str(today_template.id),
                TaskSubmission.student_id == str(current_user.id),
                TaskSubmission.class_id == m.class_id,
                TaskSubmission.status != "rejected",
            )
            if sub:
                submitted_today = True
                submission_status = sub.status
                submission_id = str(sub.id)

        classes.append({
            "class_id": m.class_id,
            "class_name": cls.name,
            "is_archived": cls.is_archived,
            "owner_id": cls.owner_id,
            "owner_display_name": owner_display_name,
            "checkin_open": checkin_result.is_open,
            "already_checked_in": existing_checkin is not None,
            "closes_at": checkin_result.closes_at.isoformat() if checkin_result.closes_at else None,
            "reason": checkin_result.reason,
            "today_template": today_template,
            "member_count": member_count,
            "submitted_today": submitted_today,
            "submission_status": submission_status,
            "submission_id": submission_id,
        })

    from gamification.badges.models import BadgeAward
    from gamification.badges.service import active_awards_query, get_student_badges
    from gamification.points.service import get_balance
    from tasks.submissions.models import TaskSubmission

    # ── Teacher pending counts (across all managed classes) ──
    class_ids = [m.class_id for m in memberships]
    pending_submission_count = 0
    pending_join_request_count = 0
    if page_ctx["can_manage_class"] or page_ctx["can_manage_tasks"]:
        if class_ids:
            from beanie.operators import In
            from core.classes.models import JoinRequest
            pending_submission_count = await TaskSubmission.find(
                In(TaskSubmission.class_id, class_ids),
                TaskSubmission.status == "pending",
            ).count()
            pending_join_request_count = await JoinRequest.find(
                In(JoinRequest.class_id, class_ids),
                JoinRequest.status == "pending",
            ).count()

    user_id = str(current_user.id)
    total_points = await get_balance(user_id)
    badge_count = await active_awards_query(BadgeAward.student_id == user_id).count()
    submission_count = await TaskSubmission.find(TaskSubmission.student_id == user_id).count()
    badges = await get_student_badges(user_id)

    # Build recent_activities from CheckinRecord, TaskSubmission, BadgeAward
    checkin_records = await CheckinRecord.find(
        CheckinRecord.student_id == user_id
    ).sort(-CheckinRecord.checked_in_at).limit(20).to_list()
    submissions = await TaskSubmission.find(
        TaskSubmission.student_id == user_id
    ).sort(-TaskSubmission.submitted_at).limit(20).to_list()
    badge_awards = await active_awards_query(
        BadgeAward.student_id == user_id
    ).sort(-BadgeAward.awarded_at).limit(20).to_list()

    activities = []
    for r in checkin_records:
        activities.append({"type": "checkin", "description": "完成每日簽到", "timestamp": r.checked_in_at})
    for s in submissions:
        activities.append({"type": "submission", "description": f"提交任務", "timestamp": s.submitted_at})
    for a in badge_awards:
        activities.append({"type": "badge", "description": f"獲得徽章", "timestamp": a.awarded_at})
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activities = activities[:20]

    # ── First-login detection ──
    is_first_login = False
    if not memberships and submission_count == 0 and current_user.created_at:
        created = current_user.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if (now - created) < timedelta(hours=24):
            is_first_login = True

    return {
        **page_ctx,
        "classes": classes,
        "stats": {
            "total_points": total_points,
            "badge_count": badge_count,
            "submission_count": submission_count,
            "streak_days": 0,
        },
        "badges": badges,
        "recent_activities": recent_activities,
        "open_create_class_modal": bool(create_class),
        "pending_submission_count": pending_submission_count,
        "pending_join_request_count": pending_join_request_count,
        "is_first_login": is_first_login,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Admin Panel — Cookie auth + admin permission guard
# ═══════════════════════════════════════════════════════════════════════════

def _build_schema():
    """Build schema list with precomputed 'all' (read|write) for templates."""
    from core.auth.permissions import PERMISSION_SCHEMA
    return [
        {
            "domain": e["domain"],
            "label": e.get("label", e["domain"]),
            "description": e.get("description", ""),
            "hide_read": e.get("hide_read", False),
            "read": int(e["read"]),
            "write": int(e["write"]),
            "all": int(e["read"]) | int(e["write"]),
        }
        for e in PERMISSION_SCHEMA
    ]


def _compute_initial_levels(permissions: int, schema: list) -> dict:
    """Return {'Self': 'none'|'read'|'readwrite', ...} for each domain."""
    levels = {}
    for entry in schema:
        has_write = bool(permissions & entry["write"])
        has_read = bool(permissions & entry["read"])
        if has_write:
            levels[entry["domain"]] = "readwrite"
        elif has_read:
            levels[entry["domain"]] = "read"
        else:
            levels[entry["domain"]] = "none"
    return levels


async def _admin_context(current_user: User) -> dict:
    """Common context injected into every admin page."""
    return await build_page_context(current_user)


async def _require_admin(current_user: User = Depends(get_page_user)) -> User:
    """Guard: user must have MANAGE_USERS or WRITE_SYSTEM."""
    from core.auth.permissions import MANAGE_USERS, WRITE_SYSTEM
    if not (current_user.permissions & MANAGE_USERS or current_user.permissions & WRITE_SYSTEM):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user


async def _require_manage_users(current_user: User = Depends(get_page_user)) -> User:
    from core.auth.permissions import MANAGE_USERS
    if not (current_user.permissions & MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user


async def _require_write_system(current_user: User = Depends(get_page_user)) -> User:
    from core.auth.permissions import WRITE_SYSTEM
    if not (current_user.permissions & WRITE_SYSTEM):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user


async def _require_manage_class(current_user: User = Depends(get_page_user)) -> User:
    from core.auth.permissions import MANAGE_ALL_CLASSES
    if not (current_user.permissions & MANAGE_ALL_CLASSES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user


@router.get("/teacher/class/{class_id}", name="teacher_class_hub_page")
@webpage.page("teacher/class_hub.html")
async def teacher_class_hub(
    request: Request,
    class_id: str,
    current_user: User = Depends(get_page_user),
):
    from core.classes.models import Class, ClassMembership
    from core.classes.service import can_manage_class
    from tasks.checkin.service import is_checkin_open
    from tasks.checkin.models import CheckinRecord
    from tasks.submissions.models import TaskSubmission
    from datetime import datetime, timezone, date, timedelta

    cls = await Class.get(class_id)
    if cls is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if not await can_manage_class(current_user, cls):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    member_count = await ClassMembership.find(ClassMembership.class_id == class_id).count()
    now = datetime.now(timezone.utc)
    checkin_result = await is_checkin_open(class_id, now)

    # Today's checkin count
    today = date.today()
    today_checkin_count = await CheckinRecord.find(
        CheckinRecord.class_id == class_id,
        CheckinRecord.checkin_date == today,
    ).count()

    # Pending submission count
    pending_submission_count = await TaskSubmission.find(
        TaskSubmission.class_id == class_id,
        TaskSubmission.status == "pending",
    ).count()

    # Weekly submission rate
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_submissions = await TaskSubmission.find(
        TaskSubmission.class_id == class_id,
        TaskSubmission.date >= week_start,
        TaskSubmission.date <= today,
    ).count()
    if member_count > 0:
        weekly_submission_rate = min(round(week_submissions / (member_count * 7) * 100, 1), 100)
    else:
        weekly_submission_rate = 0

    page_ctx = await build_page_context(current_user)

    return {
        **page_ctx,
        "class_id": class_id,
        "class_name": cls.name,
        "member_count": member_count,
        "checkin_open": checkin_result.is_open,
        "is_archived": cls.is_archived,
        "discord_webhook_url": cls.discord_webhook_url or "",
        "invite_code": cls.invite_code,
        "today_checkin_count": today_checkin_count,
        "pending_submission_count": pending_submission_count,
        "weekly_submission_rate": weekly_submission_rate,
    }


@router.get("/admin/", name="admin_overview_page")
@webpage.page("admin/index.html")
async def admin_overview(
    request: Request,
    current_user: User = Depends(_require_admin),
):
    from core.classes.models import Class

    total = await User.count()
    active_class_count = await Class.find(Class.is_archived == False).count()  # noqa: E712
    archived_class_count = await Class.find(Class.is_archived == True).count()  # noqa: E712
    return {
        **(await _admin_context(current_user)),
        "user_count": total,
        "active_class_count": active_class_count,
        "archived_class_count": archived_class_count,
        "admin_section": "overview",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.get("/admin/users/", name="admin_users_list_page")
@webpage.page("admin/users_list.html")
async def admin_users_list(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(_require_manage_users),
):
    from core.auth.permissions import ROLE_PRESETS
    skip = (page - 1) * page_size
    total = await User.count()
    users = await User.find_all().skip(skip).limit(page_size).to_list()
    return {
        **(await _admin_context(current_user)),
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "display_name": u.display_name,
                "name": u.name,
                "permissions": u.permissions,
                "tags": u.tags,
                "identity_tags": [t.value if hasattr(t, "value") else t for t in u.identity_tags],
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "presets": ROLE_PRESETS,
        "admin_section": "users",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.get("/admin/users/new", name="admin_user_new_page")
@webpage.page("admin/user_form.html")
async def admin_user_new(
    request: Request,
    current_user: User = Depends(_require_manage_users),
):
    from core.auth.permissions import ROLE_PRESETS
    schema = _build_schema()
    return {
        **(await _admin_context(current_user)),
        "edit_user": None,
        "initial_levels": {e["domain"]: "none" for e in schema},
        "schema": schema,
        "presets": ROLE_PRESETS,
        "admin_section": "users",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.post("/admin/users/new")
@webpage.redirect(status_code=302)
async def admin_user_new_submit(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    permissions: int = Form(default=0),
    tags: str = Form(default=""),
    name: str = Form(default=""),
    email: str = Form(default=""),
    class_name: str = Form(default=""),
    seat_number: int = Form(default=0),
    current_user: User = Depends(_require_manage_users),
):
    from core.auth.password import hash_password
    from core.users.models import IdentityTag, StudentProfile
    form_data = await request.form()
    identity_tag_values = form_data.getlist("identity_tags")
    valid_tags = {t.value for t in IdentityTag}
    identity_tags = [IdentityTag(v) for v in identity_tag_values if v in valid_tags]

    if not email or not email.strip():
        error_url = request.url_for("admin_user_new_page").include_query_params(error="Email 為必填欄位")
        return (str(error_url), 302)
    existing = await User.find_one(User.username == username)
    if existing:
        error_url = request.url_for("admin_user_new_page").include_query_params(error="使用者名稱已存在")
        return (str(error_url), 302)
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    student_profile = None
    if IdentityTag.STUDENT in identity_tags and (class_name or seat_number):
        student_profile = StudentProfile(class_name=class_name, seat_number=seat_number)
    user = User(
        username=username,
        hashed_password=hash_password(password),
        display_name=display_name,
        name=name,
        email=email,
        permissions=permissions,
        tags=tags_list,
        identity_tags=identity_tags,
        student_profile=student_profile,
    )
    await user.insert()
    success_url = request.url_for("admin_users_list_page").include_query_params(success="使用者已建立")
    return (str(success_url), 302)


@router.get("/admin/users/{user_id}/edit", name="admin_user_edit_page")
@webpage.page("admin/user_form.html")
async def admin_user_edit(
    request: Request,
    user_id: str,
    current_user: User = Depends(_require_manage_users),
):
    from core.auth.permissions import ROLE_PRESETS
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    schema = _build_schema()
    return {
        **(await _admin_context(current_user)),
        "edit_user": {
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "name": user.name,
            "email": user.email,
            "permissions": user.permissions,
            "tags": user.tags,
            "identity_tags": [t.value if hasattr(t, "value") else t for t in user.identity_tags],
            "student_profile": user.student_profile,
        },
        "initial_levels": _compute_initial_levels(user.permissions, schema),
        "schema": schema,
        "presets": ROLE_PRESETS,
        "admin_section": "users",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.post("/admin/users/{user_id}/edit")
@webpage.redirect(status_code=302)
async def admin_user_edit_submit(
    request: Request,
    user_id: str,
    display_name: str = Form(...),
    permissions: int = Form(default=0),
    tags: str = Form(default=""),
    new_password: str = Form(default=""),
    name: str = Form(default=""),
    email: str = Form(default=""),
    class_name: str = Form(default=""),
    seat_number: int = Form(default=0),
    current_user: User = Depends(_require_manage_users),
):
    from core.auth.password import hash_password
    from core.users.models import IdentityTag, StudentProfile
    form_data = await request.form()
    identity_tag_values = form_data.getlist("identity_tags")
    valid_tags = {t.value for t in IdentityTag}
    identity_tags = [IdentityTag(v) for v in identity_tag_values if v in valid_tags]

    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.display_name = display_name
    user.name = name
    user.email = email
    user.permissions = permissions
    user.tags = [t.strip() for t in tags.split(",") if t.strip()]
    user.identity_tags = identity_tags
    if IdentityTag.STUDENT in identity_tags:
        user.student_profile = StudentProfile(class_name=class_name, seat_number=seat_number)
    else:
        user.student_profile = None
    if new_password:
        user.hashed_password = hash_password(new_password)
    await user.save()
    success_url = request.url_for("admin_users_list_page").include_query_params(success="使用者已更新")
    return (str(success_url), 302)


# ═══════════════════════════════════════════════════════════════════════════
# Personal Settings Page
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/settings", name="settings_page")
@webpage.page("settings.html")
async def settings_page(
    request: Request,
    current_user: User = Depends(get_page_user),
):
    page_ctx = await build_page_context(current_user)
    return {
        **page_ctx,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.post("/settings/display-name", name="settings_update_display_name")
@webpage.redirect(status_code=302)
async def settings_update_display_name(
    request: Request,
    display_name: str = Form(...),
    current_user: User = Depends(get_page_user),
):
    if not display_name.strip():
        error_url = request.url_for("settings_page").include_query_params(error="顯示名稱不可為空")
        return (str(error_url), 302)
    current_user.display_name = display_name.strip()
    await current_user.save()
    success_url = request.url_for("settings_page").include_query_params(success="顯示名稱已更新")
    return (str(success_url), 302)


@router.post("/settings/password", name="settings_update_password")
@webpage.redirect(status_code=302)
async def settings_update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_page_user),
):
    from core.auth.password import hash_password, verify_password
    if not verify_password(current_password, current_user.hashed_password):
        error_url = request.url_for("settings_page").include_query_params(error="目前密碼錯誤")
        return (str(error_url), 302)
    current_user.hashed_password = hash_password(new_password)
    await current_user.save()
    success_url = request.url_for("settings_page").include_query_params(success="密碼已更新")
    return (str(success_url), 302)


@router.get("/admin/classes/", name="admin_classes_list_page")
@webpage.page("admin/classes_list.html")
async def admin_classes_list(
    request: Request,
    current_user: User = Depends(_require_manage_class),
):
    from core.classes.models import Class, ClassMembership
    all_classes = await Class.find_all().to_list()

    classes = []
    for cls in all_classes:
        member_count = await ClassMembership.find(ClassMembership.class_id == str(cls.id)).count()
        owner = await User.get(cls.owner_id) if cls.owner_id else None
        classes.append({
            "id": str(cls.id),
            "name": cls.name,
            "owner_id": cls.owner_id,
            "owner_name": owner.display_name if owner else cls.owner_id,
            "owner_display_name": owner.display_name if owner else "",
            "invite_code": cls.invite_code,
            "is_archived": cls.is_archived,
            "member_count": member_count,
        })

    return {
        **(await _admin_context(current_user)),
        "class_list": classes,
        "admin_section": "classes",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.get("/admin/system/", name="admin_system_page")
@webpage.page("admin/system_settings.html")
async def admin_system_settings(
    request: Request,
    current_user: User = Depends(_require_write_system),
):
    config = getattr(request.app.state, "system_config", None)
    return {
        **(await _admin_context(current_user)),
        "config": config,
        "admin_section": "system",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }


@router.post("/admin/system/")
@webpage.redirect(status_code=302)
async def admin_system_settings_submit(
    request: Request,
    site_name: str = Form(...),
    admin_email: str = Form(default=""),
    join_request_reject_cooldown_hours: int = Form(default=24),
    current_user: User = Depends(_require_write_system),
):
    from core.system.models import SystemConfig
    config = await SystemConfig.find_one()
    if config:
        config.site_name = site_name
        config.admin_email = admin_email
        if join_request_reject_cooldown_hours >= 0:
            config.join_request_reject_cooldown_hours = join_request_reject_cooldown_hours
        await config.save()
        request.app.state.system_config = config
        webpage.webpage_context_update({"site_name": site_name})
    success_url = request.url_for("admin_system_page").include_query_params(success="設定已儲存")
    return (str(success_url), 302)
