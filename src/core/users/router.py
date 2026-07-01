"""Admin router: user admin manages accounts."""
import csv
import io
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.auth.guards import require_permission
from core.auth.password import hash_password, validate_password_strength
from core.auth.permissions import (
    MANAGE_USERS,
    PERMISSION_SCHEMA,
    ROLE_PRESETS,
    STUDENT,
)
from core.users.models import IdentityTag, StudentProfile, User
from core.users.schemas import admin_view

router = APIRouter(prefix="/admin", tags=["admin"])

_PRESET_MAP = {p["name"]: p["value"] for p in ROLE_PRESETS}
_IDENTITY_TAG_VALUES = [t.value for t in IdentityTag]


# ── Permission schema / presets / identity-tags ───────────────────────────────

@router.get("/permissions/schema")
async def get_permission_schema(
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Return PERMISSION_SCHEMA as a JSON-serialisable list."""
    return [
        {"domain": entry["domain"], "read": int(entry["read"]), "write": int(entry["write"])}
        for entry in PERMISSION_SCHEMA
    ]


@router.get("/permissions/presets")
async def get_permission_presets(
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Return all named Role Presets with their integer values."""
    return ROLE_PRESETS


@router.get("/permissions/identity-tags")
async def get_identity_tags(
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Return all valid IdentityTag values."""
    return _IDENTITY_TAG_VALUES


# ── User CRUD ────────────────────────────────────────────────────────────────

class StudentProfileRequest(BaseModel):
    class_name: str = ""
    seat_number: int = 0


class CreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: str
    name: str = ""
    email: str = ""
    identity_tags: list[str] = []
    permissions: int = int(STUDENT)
    tags: list[str] = []
    student_profile: StudentProfileRequest | None = None


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    name: str | None = None
    email: str | None = None
    identity_tags: list[str] | None = None
    permissions: int | None = None
    tags: list[str] | None = None
    new_password: str | None = None
    student_profile: StudentProfileRequest | None = None


def _user_admin_response(user: User) -> dict:
    return admin_view(user)


@router.get("/users/check-username")
async def check_username(
    username: str,
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Check whether a username is already taken. Returns {available: bool}."""
    existing = await User.find_one(User.username == username)
    return {"available": existing is None}


@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Return a paginated list of all users."""
    skip = (page - 1) * page_size
    total = await User.count()
    users = await User.find_all().skip(skip).limit(page_size).to_list()
    return {
        "users": [_user_admin_response(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    current_user: User = Depends(require_permission(MANAGE_USERS)),
):
    """User admin creates a new user account."""
    if body.permissions & ~current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant permissions higher than your own",
        )
    try:
        validate_password_strength(body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    existing = await User.find_one(User.username == body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    parsed_tags = [IdentityTag(t) for t in body.identity_tags if t in _IDENTITY_TAG_VALUES]
    sp = StudentProfile(**body.student_profile.model_dump()) if body.student_profile else None
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        name=body.name,
        email=body.email,
        identity_tags=parsed_tags,
        permissions=body.permissions,
        tags=body.tags,
        student_profile=sp,
    )
    await user.insert()
    return _user_admin_response(user)


# ── Bulk operations (declared before /{user_id} to avoid route shadowing) ───

class BulkIdsRequest(BaseModel):
    ids: list[str]


class BulkPermissionsRequest(BaseModel):
    ids: list[str]
    permissions: int


@router.delete("/users/bulk")
async def bulk_delete_users(
    body: BulkIdsRequest,
    current_user: User = Depends(require_permission(MANAGE_USERS)),
):
    """Bulk delete users by ID list, silently excluding the caller's own ID."""
    own_id = str(current_user.id)
    target_ids = [uid for uid in body.ids if uid != own_id]
    deleted = 0
    for uid in target_ids:
        user = await User.get(uid)
        if user:
            await user.delete()
            deleted += 1
    return {"deleted": deleted}


@router.patch("/users/bulk")
async def bulk_update_permissions(
    body: BulkPermissionsRequest,
    current_user: User = Depends(require_permission(MANAGE_USERS)),
):
    """Bulk update permissions for a list of users."""
    if body.permissions & ~current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant permissions higher than your own",
        )
    updated = 0
    for uid in body.ids:
        user = await User.get(uid)
        if user:
            user.permissions = body.permissions
            await user.save()
            updated += 1
    return {"updated": updated}


# ── CSV import template ───────────────────────────────────────────────────────

_STUDENT_TEMPLATE_HEADERS = [
    "username", "password", "display_name", "name", "email",
    "identity_tag", "preset", "tags", "class_name", "seat_number",
]
_STUDENT_TEMPLATE_EXAMPLE = [
    "s001", "password123", "暱稱", "真實姓名", "student@school.edu",
    "student", "STUDENT", "", "302班", "1",
]
_STAFF_TEMPLATE_HEADERS = [
    "username", "password", "display_name", "name", "email",
    "identity_tag", "preset", "tags",
]
_STAFF_TEMPLATE_EXAMPLE = [
    "t001", "password123", "暱稱", "真實姓名", "teacher@school.edu",
    "teacher", "TEACHER", "",
]


@router.get("/users/import/template")
async def download_import_template(
    type: str = "student",
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Download a CSV template for batch user import."""
    if type == "student":
        headers = _STUDENT_TEMPLATE_HEADERS
        example = _STUDENT_TEMPLATE_EXAMPLE
        filename = "students_template.csv"
    else:
        headers = _STAFF_TEMPLATE_HEADERS
        example = _STAFF_TEMPLATE_EXAMPLE
        filename = "staff_template.csv"

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerow(example)
    content = buf.getvalue()

    return StreamingResponse(
        iter([content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Single user CRUD ──────────────────────────────────────────────────────────

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Return a single user by ID."""
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_admin_response(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: User = Depends(require_permission(MANAGE_USERS)),
):
    """Update a user's fields. identity_tags, name, email require MANAGE_USERS."""
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.permissions is not None and (body.permissions & ~current_user.permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant permissions higher than your own",
        )
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    if body.identity_tags is not None:
        user.identity_tags = [IdentityTag(t) for t in body.identity_tags if t in _IDENTITY_TAG_VALUES]
    if body.permissions is not None:
        user.permissions = body.permissions
    if body.tags is not None:
        user.tags = body.tags
    if body.new_password is not None:
        try:
            validate_password_strength(body.new_password)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        user.hashed_password = hash_password(body.new_password)
    if body.student_profile is not None:
        user.student_profile = StudentProfile(**body.student_profile.model_dump())
    await user.save()
    return _user_admin_response(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission(MANAGE_USERS)),
):
    """Delete a single user. Cannot delete own account."""
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user.delete()


# ── CSV import ───────────────────────────────────────────────────────────────

_CSV_IMPORT_MAX_BYTES = 1_048_576  # 1 MB


@router.post("/users/import")
async def import_users_csv(
    file: UploadFile = File(...),
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    """Batch-create users from a CSV file.

    Supported columns: username, password, display_name, name, email,
    identity_tag, preset, tags, class_name, seat_number
    """
    content = await file.read()
    if len(content) > _CSV_IMPORT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large. Maximum allowed size is 1 MB.",
        )
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    success = 0
    failed: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        username     = (row.get("username") or "").strip()
        password     = (row.get("password") or "").strip()
        display_name = (row.get("display_name") or "").strip()
        name         = (row.get("name") or "").strip()
        email        = (row.get("email") or "").strip()
        identity_tag = (row.get("identity_tag") or "").strip().lower()
        preset_name  = (row.get("preset") or "").strip().upper()
        tags_raw     = (row.get("tags") or "").strip()
        class_name   = (row.get("class_name") or "").strip()
        seat_number_raw = (row.get("seat_number") or "").strip()

        if preset_name not in _PRESET_MAP:
            failed.append({"row": row_num, "reason": f"Unknown preset: {preset_name!r}"})
            continue

        if identity_tag and identity_tag not in _IDENTITY_TAG_VALUES:
            failed.append({"row": row_num, "reason": f"Unknown identity tag: {identity_tag!r}"})
            continue

        try:
            validate_password_strength(password)
        except ValueError as e:
            failed.append({"row": row_num, "reason": str(e)})
            continue

        existing = await User.find_one(User.username == username)
        if existing:
            failed.append({"row": row_num, "reason": f"Username already exists: {username!r}"})
            continue

        tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []
        identity_tags = [IdentityTag(identity_tag)] if identity_tag else []

        sp = None
        if class_name or seat_number_raw:
            try:
                seat_number = int(seat_number_raw) if seat_number_raw else 0
            except ValueError:
                seat_number = 0
            sp = StudentProfile(class_name=class_name, seat_number=seat_number)

        user = User(
            username=username,
            hashed_password=hash_password(password),
            display_name=display_name,
            name=name,
            email=email,
            identity_tags=identity_tags,
            permissions=_PRESET_MAP[preset_name],
            tags=tags,
            student_profile=sp,
        )
        await user.insert()
        success += 1

    return {"success": success, "failed": failed}
