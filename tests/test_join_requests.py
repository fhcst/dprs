"""Tests for join-request-review feature (TDD red phase)."""
import pytest
from datetime import datetime, timezone, timedelta
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_join_requests")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership, JoinRequest
    from core.system.models import SystemConfig
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership, JoinRequest, SystemConfig],
    )
    yield database
    client.close()


@pytest.fixture
async def teacher(db):
    from core.users.models import User, IdentityTag
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    u = User(
        username="teach",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
        identity_tags=[IdentityTag.TEACHER],
    )
    await u.insert()
    return u


@pytest.fixture
async def student(db):
    from core.users.models import User, IdentityTag
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT
    u = User(
        username="stu",
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
    )
    await u.insert()
    return u


@pytest.fixture
async def system_config(db):
    from core.system.models import SystemConfig
    config = SystemConfig(
        site_name="Test",
        admin_email="test@test.com",
        join_request_reject_cooldown_hours=24,
    )
    await config.insert()
    return config


@pytest.fixture
async def cls(db, teacher):
    from core.classes.service import create_class
    return await create_class(
        name="Test Class",
        description="A test class",
        visibility="public",
        owner=teacher,
    )


# ---------------------------------------------------------------------------
# Task 2.1: JoinRequest model tests
# ---------------------------------------------------------------------------


async def test_join_request_model_fields(db, student, cls):
    """Create a JoinRequest and verify all fields are stored correctly."""
    from core.classes.models import JoinRequest

    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="pending",
        invite_code_used=cls.invite_code,
        reviewed_at=None,
        reviewed_by=None,
    )
    await jr.insert()

    fetched = await JoinRequest.get(jr.id)
    assert fetched is not None
    assert fetched.class_id == str(cls.id)
    assert fetched.user_id == str(student.id)
    assert fetched.status == "pending"
    assert fetched.invite_code_used == cls.invite_code
    assert fetched.reviewed_at is None
    assert fetched.reviewed_by is None
    assert fetched.requested_at is not None


async def test_join_request_default_status_is_pending(db, student, cls):
    """JoinRequest status should default to 'pending' when not specified."""
    from core.classes.models import JoinRequest

    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        invite_code_used=cls.invite_code,
    )
    assert jr.status == "pending"


async def test_join_request_unique_pending_constraint(db, student, cls, system_config):
    """Two pending requests for the same class+user should be caught by service logic."""
    from core.classes.service import create_join_request

    await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)
    with pytest.raises(ValueError):
        await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)


# ---------------------------------------------------------------------------
# Task 2.2: Student submit join request API tests
# ---------------------------------------------------------------------------


async def test_create_join_request_valid(db, student, cls, system_config):
    """Valid invite code should return a JoinRequest with status=pending."""
    from core.classes.service import create_join_request

    jr = await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)
    assert jr.status == "pending"
    assert jr.class_id == str(cls.id)
    assert jr.user_id == str(student.id)
    assert jr.invite_code_used == cls.invite_code


async def test_create_join_request_invalid_code(db, student, system_config):
    """Invalid invite code should raise ValueError."""
    from core.classes.service import create_join_request

    with pytest.raises(ValueError):
        await create_join_request(user=student, invite_code="INVALID_CODE", cooldown_hours=24)


async def test_create_join_request_already_member(db, student, cls, system_config):
    """A user who is already a class member should be rejected."""
    from core.classes.service import create_join_request, join_class_by_code

    # First make the student a member directly
    await join_class_by_code(student, cls.invite_code)

    with pytest.raises(ValueError):
        await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)


async def test_create_join_request_duplicate_pending(db, student, cls, system_config):
    """A duplicate pending request for the same class should raise ValueError."""
    from core.classes.service import create_join_request

    await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)
    with pytest.raises(ValueError):
        await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)


async def test_create_join_request_within_cooldown(db, student, cls, teacher, system_config):
    """Reapplying within the cooldown period after rejection should raise ValueError."""
    from core.classes.models import JoinRequest
    from core.classes.service import create_join_request

    # Create a rejected request with reviewed_at = now (within cooldown)
    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="rejected",
        invite_code_used=cls.invite_code,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=str(teacher.id),
    )
    await jr.insert()

    with pytest.raises(ValueError):
        await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)


async def test_create_join_request_cooldown_zero_allows_reapply(db, student, cls, teacher, system_config):
    """When cooldown is 0, reapplying after rejection should succeed immediately."""
    from core.classes.models import JoinRequest
    from core.classes.service import create_join_request

    # Create a rejected request
    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="rejected",
        invite_code_used=cls.invite_code,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=str(teacher.id),
    )
    await jr.insert()

    # With cooldown=0, should succeed
    new_jr = await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=0)
    assert new_jr.status == "pending"


async def test_create_join_request_non_student_rejected(db, cls, system_config):
    """A user without the STUDENT identity_tag should be rejected."""
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT as STUDENT_PERMS
    from core.classes.service import create_join_request

    # Create a user WITHOUT the student identity tag
    non_student = User(
        username="notstudent",
        hashed_password=hash_password("pw"),
        display_name="Not A Student",
        permissions=int(STUDENT_PERMS),
        identity_tags=[],  # No identity tags
    )
    await non_student.insert()

    with pytest.raises(ValueError):
        await create_join_request(user=non_student, invite_code=cls.invite_code, cooldown_hours=24)


# ---------------------------------------------------------------------------
# Task 2.3: Rate limiting tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Rate limiting tested via integration tests at the router level")
async def test_join_request_rate_limit_placeholder(db):
    """Placeholder — rate limiting is enforced at the router level, not in service."""
    pass


# ---------------------------------------------------------------------------
# Task 2.4: Teacher view pending requests
# ---------------------------------------------------------------------------


async def test_get_pending_join_requests_returns_pending_only(db, student, cls, teacher):
    """Only pending requests should be returned; approved and rejected are excluded."""
    from core.classes.models import JoinRequest
    from core.classes.service import get_pending_join_requests

    # Create one pending request
    pending = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="pending",
        invite_code_used=cls.invite_code,
    )
    await pending.insert()

    # Create an approved request (different user simulated via different user_id)
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT as STUDENT_PERMS
    from core.users.models import IdentityTag

    stu2 = User(
        username="stu2",
        hashed_password=hash_password("pw"),
        display_name="Student 2",
        permissions=int(STUDENT_PERMS),
        identity_tags=[IdentityTag.STUDENT],
    )
    await stu2.insert()

    approved = JoinRequest(
        class_id=str(cls.id),
        user_id=str(stu2.id),
        status="approved",
        invite_code_used=cls.invite_code,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=str(teacher.id),
    )
    await approved.insert()

    stu3 = User(
        username="stu3",
        hashed_password=hash_password("pw"),
        display_name="Student 3",
        permissions=int(STUDENT_PERMS),
        identity_tags=[IdentityTag.STUDENT],
    )
    await stu3.insert()

    rejected = JoinRequest(
        class_id=str(cls.id),
        user_id=str(stu3.id),
        status="rejected",
        invite_code_used=cls.invite_code,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=str(teacher.id),
    )
    await rejected.insert()

    results = await get_pending_join_requests(class_id=str(cls.id))
    assert len(results) == 1
    assert results[0].status == "pending"
    assert results[0].user_id == str(student.id)


async def test_get_pending_join_requests_empty(db, cls):
    """No requests should return an empty list."""
    from core.classes.service import get_pending_join_requests

    results = await get_pending_join_requests(class_id=str(cls.id))
    assert results == []


# ---------------------------------------------------------------------------
# Task 2.5: Teacher review join request
# ---------------------------------------------------------------------------


async def test_review_approve_creates_membership(db, student, cls, teacher):
    """Approving a join request should create a ClassMembership for the student."""
    from core.classes.models import JoinRequest, ClassMembership
    from core.classes.service import review_join_request

    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="pending",
        invite_code_used=cls.invite_code,
    )
    await jr.insert()

    result = await review_join_request(
        request_id=str(jr.id),
        action="approved",
        reviewer=teacher,
    )

    assert result.status == "approved"
    assert result.reviewed_at is not None
    assert result.reviewed_by == str(teacher.id)

    # Verify ClassMembership was created
    membership = await ClassMembership.find_one(
        ClassMembership.class_id == str(cls.id),
        ClassMembership.user_id == str(student.id),
    )
    assert membership is not None
    assert membership.role == "student"


async def test_review_reject_updates_status(db, student, cls, teacher):
    """Rejecting a join request should set status to rejected and record reviewed_at."""
    from core.classes.models import JoinRequest
    from core.classes.service import review_join_request

    jr = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="pending",
        invite_code_used=cls.invite_code,
    )
    await jr.insert()

    result = await review_join_request(
        request_id=str(jr.id),
        action="rejected",
        reviewer=teacher,
    )

    assert result.status == "rejected"
    assert result.reviewed_at is not None
    assert result.reviewed_by == str(teacher.id)


async def test_review_non_pending_raises(db, student, cls, teacher):
    """Reviewing an already-approved or already-rejected request should raise ValueError."""
    from core.classes.models import JoinRequest
    from core.classes.service import review_join_request

    # Already approved
    jr_approved = JoinRequest(
        class_id=str(cls.id),
        user_id=str(student.id),
        status="approved",
        invite_code_used=cls.invite_code,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=str(teacher.id),
    )
    await jr_approved.insert()

    with pytest.raises(ValueError):
        await review_join_request(
            request_id=str(jr_approved.id),
            action="rejected",
            reviewer=teacher,
        )


async def test_review_not_found_raises(db, teacher):
    """Reviewing a non-existent join request ID should raise ValueError."""
    from core.classes.service import review_join_request
    from bson import ObjectId

    fake_id = str(ObjectId())
    with pytest.raises(ValueError):
        await review_join_request(
            request_id=fake_id,
            action="approved",
            reviewer=teacher,
        )


# ---------------------------------------------------------------------------
# Task 2.6: Invite code join behavior change
# ---------------------------------------------------------------------------


async def test_join_class_by_code_creates_join_request(db, student, cls, system_config):
    """
    After implementation, joining by invite code should create a JoinRequest
    instead of directly creating a membership.

    For now, this tests the NEW create_join_request function which replaces the
    old join_class_by_code behavior for students.
    """
    from core.classes.service import create_join_request
    from core.classes.models import JoinRequest

    jr = await create_join_request(user=student, invite_code=cls.invite_code, cooldown_hours=24)

    assert isinstance(jr, JoinRequest)
    assert jr.status == "pending"
    assert jr.class_id == str(cls.id)
    assert jr.user_id == str(student.id)
    assert jr.invite_code_used == cls.invite_code


# ---------------------------------------------------------------------------
# Task 2.7: SystemConfig cooldown field tests
# ---------------------------------------------------------------------------


async def test_system_config_has_cooldown_field(db):
    """SystemConfig should have join_request_reject_cooldown_hours defaulting to 24."""
    from core.system.models import SystemConfig

    config = SystemConfig(site_name="Test Site", admin_email="a@b.com")
    assert config.join_request_reject_cooldown_hours == 24


async def test_system_config_cooldown_zero_valid(db):
    """Setting cooldown to 0 should be valid (disables cooldown)."""
    from core.system.models import SystemConfig

    config = SystemConfig(
        site_name="Test Site",
        admin_email="a@b.com",
        join_request_reject_cooldown_hours=0,
    )
    assert config.join_request_reject_cooldown_hours == 0
    await config.insert()
    fetched = await SystemConfig.get(config.id)
    assert fetched.join_request_reject_cooldown_hours == 0


@pytest.mark.skip(reason="Negative validation will be enforced at the router level, not at model level")
async def test_system_config_cooldown_negative_invalid(db):
    """Negative cooldown values should be rejected (enforced at router, not model)."""
    pass
