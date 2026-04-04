"""Tests for invite enumerate feature — list_students_for_invite and GET /classes/{id}/invite/students."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_invite_enumerate")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership],
    )
    yield database
    client.close()


async def _make_user(
    username,
    permissions_val,
    identity_tags=None,
    student_profile=None,
    tags=None,
    display_name=None,
):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name=display_name or username.capitalize(),
        permissions=permissions_val,
        identity_tags=identity_tags or [],
        student_profile=student_profile,
        tags=tags or [],
    )
    await u.insert()
    return u


async def _make_user_with_token(
    username,
    permissions_val,
    identity_tags=None,
    student_profile=None,
    tags=None,
    display_name=None,
):
    from core.auth.jwt import create_access_token
    user = await _make_user(
        username, permissions_val,
        identity_tags=identity_tags,
        student_profile=student_profile,
        tags=tags,
        display_name=display_name,
    )
    token = create_access_token(user_id=str(user.id), permissions=permissions_val)
    return user, token


# ---------------------------------------------------------------------------
# Task 3.1: Service function tests — list_students_for_invite
# ---------------------------------------------------------------------------


async def test_excludes_students_already_in_class(db):
    """Students who are already members of the class must not appear in the result."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag, StudentProfile
    from core.classes.service import create_class, list_students_for_invite
    from core.classes.models import ClassMembership

    teacher = await _make_user("teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER])
    cls = await create_class("Test Class", "", "public", teacher)

    # Create three students
    stu_a = await _make_user(
        "stu_a", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="101", seat_number=1),
    )
    stu_b = await _make_user(
        "stu_b", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="101", seat_number=2),
    )
    stu_c = await _make_user(
        "stu_c", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="102", seat_number=1),
    )

    # Add stu_a and stu_b as members of the class
    await ClassMembership(
        class_id=str(cls.id), user_id=str(stu_a.id), role="student",
    ).insert()
    await ClassMembership(
        class_id=str(cls.id), user_id=str(stu_b.id), role="student",
    ).insert()

    students, total = await list_students_for_invite(str(cls.id))
    student_ids = [s["user_id"] for s in students]

    # stu_a and stu_b are members — must be excluded
    assert str(stu_a.id) not in student_ids
    assert str(stu_b.id) not in student_ids
    # stu_c is NOT a member — must be included
    assert str(stu_c.id) in student_ids
    assert total == 1


async def test_sorts_by_class_name_asc_then_seat_number_asc(db):
    """Results must be sorted by class_name ASC (empty last) then seat_number ASC."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag, StudentProfile
    from core.classes.service import create_class, list_students_for_invite

    teacher = await _make_user("teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER])
    cls = await create_class("Sort Class", "", "public", teacher)

    # Create students with various class_name / seat_number combos
    await _make_user(
        "s_302_5", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="302", seat_number=5),
    )
    await _make_user(
        "s_101_3", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="101", seat_number=3),
    )
    await _make_user(
        "s_101_1", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="101", seat_number=1),
    )
    await _make_user(
        "s_no_class", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="", seat_number=0),
    )
    await _make_user(
        "s_302_1", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="302", seat_number=1),
    )

    students, total = await list_students_for_invite(str(cls.id))
    assert total == 5

    # Expected order: 101/1, 101/3, 302/1, 302/5, empty/0
    expected_usernames = ["s_101_1", "s_101_3", "s_302_1", "s_302_5", "s_no_class"]
    actual_display_names = [s["display_name"] for s in students]
    # display_name is username.capitalize() from _make_user
    expected_display_names = [u.capitalize() for u in expected_usernames]
    assert actual_display_names == expected_display_names


async def test_pagination_offset_limit(db):
    """offset/limit pagination must return the correct slice."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag, StudentProfile
    from core.classes.service import create_class, list_students_for_invite

    teacher = await _make_user("teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER])
    cls = await create_class("Page Class", "", "public", teacher)

    # Create 5 students in known sort order (all same class_name, different seats)
    for i in range(1, 6):
        await _make_user(
            f"pstu{i}", int(STUDENT),
            identity_tags=[IdentityTag.STUDENT],
            student_profile=StudentProfile(class_name="101", seat_number=i),
        )

    # Request page 2 of size 2 (offset=2, limit=2) → seats 3, 4
    students, total = await list_students_for_invite(str(cls.id), offset=2, limit=2)
    assert total == 5
    assert len(students) == 2
    assert students[0]["seat_number"] == 3
    assert students[1]["seat_number"] == 4


async def test_offset_beyond_total_returns_empty(db):
    """Offset beyond total count must return empty students list but correct total."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag, StudentProfile
    from core.classes.service import create_class, list_students_for_invite

    teacher = await _make_user("teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER])
    cls = await create_class("Beyond Class", "", "public", teacher)

    # Create 3 students
    for i in range(1, 4):
        await _make_user(
            f"bstu{i}", int(STUDENT),
            identity_tags=[IdentityTag.STUDENT],
            student_profile=StudentProfile(class_name="201", seat_number=i),
        )

    students, total = await list_students_for_invite(str(cls.id), offset=100, limit=10)
    assert total == 3
    assert students == []


# ---------------------------------------------------------------------------
# Task 3.2: API endpoint tests — GET /classes/{class_id}/invite/students
# ---------------------------------------------------------------------------


@pytest.fixture
def class_app():
    from fastapi import FastAPI
    from core.classes.router import router
    app = FastAPI()
    app.include_router(router)
    return app


async def test_api_response_format(db, class_app):
    """Response must include students, total, offset, limit keys."""
    from core.auth.permissions import TEACHER
    from core.users.models import IdentityTag
    from core.classes.service import create_class

    teacher, token = await _make_user_with_token(
        "teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER],
    )
    cls = await create_class("API Class", "", "public", teacher)

    async with AsyncClient(transport=ASGITransport(app=class_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get(f"/classes/{cls.id}/invite/students")

    assert resp.status_code == 200
    data = resp.json()
    assert "students" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data


async def test_api_unauthorized_non_teacher_gets_403(db, class_app):
    """A non-teacher (student-only permissions) must receive HTTP 403."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag
    from core.classes.service import create_class

    # Create a teacher who owns the class
    teacher = await _make_user(
        "teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER],
    )
    cls = await create_class("Forbidden Class", "", "public", teacher)

    # Create a student user (non-teacher) and get a token for them
    _, student_token = await _make_user_with_token(
        "stu", int(STUDENT), identity_tags=[IdentityTag.STUDENT],
    )

    async with AsyncClient(transport=ASGITransport(app=class_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", student_token)
        resp = await ac.get(f"/classes/{cls.id}/invite/students")

    assert resp.status_code == 403


async def test_api_response_includes_tags_field(db, class_app):
    """Each student object in the response must include a tags field."""
    from core.auth.permissions import TEACHER, STUDENT
    from core.users.models import IdentityTag, StudentProfile
    from core.classes.service import create_class

    teacher, token = await _make_user_with_token(
        "teach", int(TEACHER), identity_tags=[IdentityTag.TEACHER],
    )
    cls = await create_class("Tags Class", "", "public", teacher)

    # Create a student with tags
    await _make_user(
        "tagged_stu", int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
        student_profile=StudentProfile(class_name="301", seat_number=7),
        tags=["vip", "transfer"],
    )

    async with AsyncClient(transport=ASGITransport(app=class_app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get(f"/classes/{cls.id}/invite/students")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    student_entry = data["students"][0]
    assert "tags" in student_entry
    assert student_entry["tags"] == ["vip", "transfer"]
