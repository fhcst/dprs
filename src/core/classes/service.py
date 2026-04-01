"""Class management service functions."""
import secrets
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from core.classes.models import Class, ClassMembership, JoinRequest
from core.auth.permissions import MANAGE_ALL_CLASSES, MANAGE_OWN_CLASS
from core.users.models import IdentityTag, User


def _new_invite_code() -> str:
    """Generate a URL-safe 8-character invite code."""
    return secrets.token_urlsafe(6).upper()[:8]


async def can_manage_class(user: User, cls: Class) -> bool:
    """
    Return True if user is authorised to manage cls.

    Rules (design: can_manage() 集中在 service 層判斷):
    - MANAGE_ALL_CLASSES → always True (classmanager level)
    - MANAGE_OWN_CLASS   → True only if user has a 'teacher' membership in cls
    """
    if user.permissions & MANAGE_ALL_CLASSES:
        return True
    if user.permissions & MANAGE_OWN_CLASS:
        membership = await ClassMembership.find_one(
            ClassMembership.class_id == str(cls.id),
            ClassMembership.user_id == str(user.id),
        )
        return membership is not None and membership.role == "teacher"
    return False


async def create_class(
    name: str,
    description: str,
    visibility: str,
    owner: User,
) -> Class:
    """Create a new class and assign the owner membership."""
    cls = Class(
        name=name,
        description=description,
        visibility=visibility,
        owner_id=str(owner.id),
        invite_code=_new_invite_code(),
    )
    await cls.insert()

    # Owner also gets a membership record as teacher
    membership = ClassMembership(
        class_id=str(cls.id),
        user_id=str(owner.id),
        role="teacher",
    )
    try:
        await membership.insert()
    except DuplicateKeyError:
        pass  # Already a member — safe to ignore
    return cls


async def join_class_by_code(user: User, invite_code: str) -> ClassMembership:
    """
    Add a user to a class using an invite code.
    Returns existing membership if already a member (idempotent).
    Raises ValueError if the code is invalid.
    """
    cls = await Class.find_one(Class.invite_code == invite_code)
    if cls is None:
        raise ValueError(f"Invalid invite code: {invite_code!r}")

    existing = await ClassMembership.find_one(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(user.id),
    )
    if existing:
        return existing

    membership = ClassMembership(
        class_id=str(cls.id),
        user_id=str(user.id),
        role="student",
    )
    try:
        await membership.insert()
    except DuplicateKeyError:
        # Concurrent join — re-fetch the existing membership
        existing = await ClassMembership.find_one(
            ClassMembership.class_id == str(cls.id),
            ClassMembership.user_id == str(user.id),
        )
        return existing
    return membership


async def join_class_by_id(user: User, class_id: str) -> ClassMembership:
    """Add a user to a public class by class ID."""
    cls = await Class.get(class_id)
    if cls is None or cls.visibility != "public":
        raise ValueError("Class not found or not public")

    existing = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == str(user.id),
    )
    if existing:
        return existing

    membership = ClassMembership(
        class_id=class_id,
        user_id=str(user.id),
        role="student",
    )
    try:
        await membership.insert()
    except DuplicateKeyError:
        existing = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == str(user.id),
        )
        return existing
    return membership


async def get_public_classes() -> list[Class]:
    """Return all public non-archived classes."""
    return await Class.find(Class.visibility == "public", Class.is_archived == False).to_list()


async def get_class_members(class_id: str) -> list[ClassMembership]:
    """Return all memberships for a class."""
    return await ClassMembership.find(ClassMembership.class_id == class_id).to_list()


async def remove_member(class_id: str, user_id: str) -> None:
    """Remove a user from a class."""
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == user_id,
    )
    if membership:
        await membership.delete()


async def promote_to_teacher(class_id: str, user_id: str) -> ClassMembership:
    """Promote a student membership to teacher role."""
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == user_id,
    )
    if membership is None:
        raise ValueError("User is not a member of this class")
    membership.role = "teacher"
    await membership.save()
    return membership


async def regenerate_invite_code(class_id: str) -> str:
    """
    Generate a new invite code for a class.
    The old code becomes invalid immediately.
    Returns the new code.
    """
    cls = await Class.get(class_id)
    if cls is None:
        raise ValueError("Class not found")
    cls.invite_code = _new_invite_code()
    await cls.save()
    return cls.invite_code


async def set_visibility(class_id: str, visibility: str) -> Class:
    """Update class visibility (public/private)."""
    cls = await Class.get(class_id)
    if cls is None:
        raise ValueError("Class not found")
    cls.visibility = visibility
    await cls.save()
    return cls


async def search_students_for_invite(
    class_id: str,
    q: str,
    search_type: str = "name",
) -> list[dict]:
    """
    Search for students not yet in class_id.
    search_type: 'name' searches User.name, 'class_name' searches student_profile.class_name
    Returns list of {user_id, display_name, name, class_name, seat_number}.
    """
    # Get existing member IDs
    memberships = await ClassMembership.find(
        ClassMembership.class_id == class_id
    ).to_list()
    member_ids = {m.user_id for m in memberships}

    # Find all users with STUDENT identity tag
    all_students = await User.find(
        User.identity_tags == IdentityTag.STUDENT
    ).to_list()

    results = []
    q_lower = q.lower()
    for user in all_students:
        if str(user.id) in member_ids:
            continue
        if search_type == "class_name":
            field_val = (user.student_profile.class_name if user.student_profile else "").lower()
        else:
            field_val = user.name.lower()
        if q_lower in field_val:
            results.append({
                "user_id": str(user.id),
                "display_name": user.display_name,
                "name": user.name,
                "class_name": user.student_profile.class_name if user.student_profile else "",
                "seat_number": user.student_profile.seat_number if user.student_profile else 0,
            })
    return results


async def batch_invite_students(class_id: str, user_ids: list[str]) -> int:
    """
    Directly add users to a class as students. Silently skips existing members.
    Returns count of newly added members.
    """
    added = 0
    for uid in user_ids:
        existing = await ClassMembership.find_one(
            ClassMembership.class_id == class_id,
            ClassMembership.user_id == uid,
        )
        if existing:
            continue
        membership = ClassMembership(
            class_id=class_id,
            user_id=uid,
            role="student",
        )
        try:
            await membership.insert()
            added += 1
        except DuplicateKeyError:
            pass  # Concurrent insert — skip
    return added


async def create_join_request(
    user: User,
    invite_code: str,
    cooldown_hours: int = 24,
) -> JoinRequest:
    """
    Create a pending JoinRequest for a class via invite code.

    Validates: invite code, not already a member, no duplicate pending,
    identity_tag is student, and rejection cooldown has elapsed.
    """
    if IdentityTag.STUDENT not in user.identity_tags:
        raise ValueError("Only students can submit join requests")

    cls = await Class.find_one(Class.invite_code == invite_code)
    if cls is None:
        raise ValueError("Invalid invite code")

    class_id = str(cls.id)
    user_id = str(user.id)

    # Already a member?
    existing_member = await ClassMembership.find_one(
        ClassMembership.class_id == class_id,
        ClassMembership.user_id == user_id,
    )
    if existing_member:
        raise ValueError("Already a member of this class")

    # Duplicate pending?
    existing_pending = await JoinRequest.find_one(
        JoinRequest.class_id == class_id,
        JoinRequest.user_id == user_id,
        JoinRequest.status == "pending",
    )
    if existing_pending:
        raise ValueError("A pending request already exists for this class")

    # Rejection cooldown check
    if cooldown_hours > 0:
        latest_rejected = await JoinRequest.find(
            JoinRequest.class_id == class_id,
            JoinRequest.user_id == user_id,
            JoinRequest.status == "rejected",
        ).sort("-reviewed_at").first_or_none()
        if latest_rejected and latest_rejected.reviewed_at:
            reviewed_at = latest_rejected.reviewed_at
            if reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
            cooldown_end = reviewed_at + timedelta(hours=cooldown_hours)
            if datetime.now(timezone.utc) < cooldown_end:
                raise ValueError("Must wait before reapplying after rejection")

    join_request = JoinRequest(
        class_id=class_id,
        user_id=user_id,
        invite_code_used=invite_code,
    )
    await join_request.insert()
    return join_request


async def get_pending_join_requests(class_id: str) -> list[JoinRequest]:
    """Return all pending JoinRequests for a class."""
    return await JoinRequest.find(
        JoinRequest.class_id == class_id,
        JoinRequest.status == "pending",
    ).to_list()


async def review_join_request(
    request_id: str,
    action: str,
    reviewer: User,
    class_id: str | None = None,
) -> JoinRequest:
    """
    Approve or reject a pending JoinRequest.

    On approve: creates ClassMembership (idempotent) and updates status.
    On reject: updates status and reviewed_at.

    Args:
        class_id: If provided, validates that the JoinRequest belongs to this class.
    """
    jr = await JoinRequest.get(request_id)
    if jr is None:
        raise ValueError("Join request not found")

    if class_id is not None and jr.class_id != class_id:
        raise ValueError("Join request does not belong to the specified class")

    if jr.status != "pending":
        raise ValueError("Only pending requests can be reviewed")

    if action not in ("approve", "approved", "reject", "rejected"):
        raise ValueError(f"Invalid action: {action!r}. Must be 'approve' or 'reject'")

    now = datetime.now(timezone.utc)
    jr.reviewed_at = now
    jr.reviewed_by = str(reviewer.id)

    if action in ("approve", "approved"):
        # Create membership FIRST — if this fails, status stays pending (retryable).
        # If status update fails after this, membership exists but request is
        # still pending; a retry will hit ensure_membership (idempotent) then save.
        await ensure_membership(jr.class_id, jr.user_id)
        jr.status = "approved"
        await jr.save()
    else:
        jr.status = "rejected"
        await jr.save()

    return jr


async def ensure_membership(class_id: str, user_id: str) -> None:
    """Atomically ensure a ClassMembership exists (race-safe, truly idempotent).

    Uses MongoDB's update_one with upsert=True so concurrent calls
    cannot produce duplicate documents.
    """
    await ClassMembership.get_pymongo_collection().update_one(
        {"class_id": class_id, "user_id": user_id},
        {"$setOnInsert": {
            "class_id": class_id,
            "user_id": user_id,
            "role": "student",
            "joined_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
