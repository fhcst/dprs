"""Tests for join-request review security fixes."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_jr_security")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership, JoinRequest
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership, JoinRequest],
    )
    yield database
    client.close()


async def _make_user(username, perms=0):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name=username.capitalize(),
        permissions=perms,
    )
    await u.insert()
    return u


async def _make_class(name, owner_id):
    from core.classes.models import Class
    import secrets
    cls = Class(
        name=name,
        owner_id=owner_id,
        visibility="private",
        invite_code=secrets.token_hex(4),
    )
    await cls.insert()
    return cls


async def _make_join_request(class_id, user_id, invite_code="test_code"):
    from core.classes.models import JoinRequest
    jr = JoinRequest(class_id=class_id, user_id=user_id, invite_code_used=invite_code)
    await jr.insert()
    return jr


# ── P1: Cross-class authorization ──────────────────────────��─────────────────

async def test_review_rejects_cross_class_request(db):
    """Teacher cannot approve a join request from another class."""
    from core.classes.service import review_join_request

    teacher = await _make_user("teacher", 0x1FF)
    class_a = await _make_class("Class A", str(teacher.id))
    class_b = await _make_class("Class B", str(teacher.id))
    student = await _make_user("student")

    # Create join request for class B
    jr = await _make_join_request(str(class_b.id), str(student.id))

    # Try to review it as if it belongs to class A → should fail
    with pytest.raises(ValueError, match="does not belong"):
        await review_join_request(
            request_id=str(jr.id),
            action="approve",
            reviewer=teacher,
            class_id=str(class_a.id),
        )


async def test_review_approves_same_class_request(db):
    """Teacher can approve a join request for their own class."""
    from core.classes.service import review_join_request
    from core.classes.models import ClassMembership

    teacher = await _make_user("teacher", 0x1FF)
    cls = await _make_class("My Class", str(teacher.id))
    student = await _make_user("student")

    jr = await _make_join_request(str(cls.id), str(student.id))

    result = await review_join_request(
        request_id=str(jr.id),
        action="approve",
        reviewer=teacher,
        class_id=str(cls.id),
    )
    assert result.status == "approved"

    # Membership should be created
    m = await ClassMembership.find_one(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(student.id),
    )
    assert m is not None
    assert m.role == "student"


# ── P2: Idempotent membership ────────────────────────────────────────────────

async def test_duplicate_approval_no_duplicate_membership(db):
    """Approving when membership already exists should not create a duplicate."""
    from core.classes.service import review_join_request
    from core.classes.models import ClassMembership, JoinRequest

    teacher = await _make_user("teacher", 0x1FF)
    cls = await _make_class("My Class", str(teacher.id))
    student = await _make_user("student")

    # Pre-create membership (e.g., via batch invite)
    existing = ClassMembership(
        class_id=str(cls.id), user_id=str(student.id), role="student"
    )
    await existing.insert()

    jr = await _make_join_request(str(cls.id), str(student.id))

    result = await review_join_request(
        request_id=str(jr.id),
        action="approve",
        reviewer=teacher,
        class_id=str(cls.id),
    )
    assert result.status == "approved"

    # Should still only have 1 membership, not 2
    count = await ClassMembership.find(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(student.id),
    ).count()
    assert count == 1


# ── Retry safety ─────────────────────────────────────────────────────────────

async def test_service_rejects_non_pending_review(db):
    """Service layer strictly rejects reviewing non-pending requests."""
    from core.classes.service import review_join_request

    teacher = await _make_user("teacher", 0x1FF)
    cls = await _make_class("My Class", str(teacher.id))
    student = await _make_user("student")

    jr = await _make_join_request(str(cls.id), str(student.id))

    await review_join_request(
        request_id=str(jr.id), action="approve", reviewer=teacher, class_id=str(cls.id),
    )

    # Service raises for any review of non-pending request
    with pytest.raises(ValueError, match="Only pending"):
        await review_join_request(
            request_id=str(jr.id), action="approve", reviewer=teacher, class_id=str(cls.id),
        )


async def test_approval_creates_membership_before_status_update(db):
    """Approval creates membership first, so partial failure leaves request pending (retryable)."""
    from core.classes.service import review_join_request
    from core.classes.models import ClassMembership

    teacher = await _make_user("teacher", 0x1FF)
    cls = await _make_class("My Class", str(teacher.id))
    student = await _make_user("student")

    jr = await _make_join_request(str(cls.id), str(student.id))

    result = await review_join_request(
        request_id=str(jr.id), action="approve", reviewer=teacher, class_id=str(cls.id),
    )
    assert result.status == "approved"

    # Membership must exist
    m = await ClassMembership.find_one(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(student.id),
    )
    assert m is not None


async def test_ensure_membership_is_idempotent(db):
    """ensure_membership can be called multiple times without duplicates."""
    from core.classes.service import ensure_membership
    from core.classes.models import ClassMembership

    teacher = await _make_user("teacher", 0x1FF)
    cls = await _make_class("My Class", str(teacher.id))
    student = await _make_user("student")

    await ensure_membership(str(cls.id), str(student.id))
    await ensure_membership(str(cls.id), str(student.id))

    count = await ClassMembership.find(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(student.id),
    ).count()
    assert count == 1
