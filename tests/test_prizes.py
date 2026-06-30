"""Tests for prize preview."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_prizes")
    from core.users.models import User
    from gamification.prizes.models import Prize
    await init_beanie(database=database, document_models=[User, Prize])
    yield database
    client.close()


@pytest.fixture
async def teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(username="tchr", hashed_password=hash_password("pw"), display_name="T", role="teacher")
    await u.insert()
    return u


async def test_create_prize(db, teacher):
    from gamification.prizes.models import Prize
    prize = Prize(
        class_id="cls1", title="書券", prize_type="physical",
        point_cost=100, created_by=str(teacher.id),
    )
    await prize.insert()
    found = await Prize.get(prize.id)
    assert found.title == "書券"
    assert found.prize_type == "physical"


async def test_only_visible_prizes_for_students(db, teacher):
    from gamification.prizes.models import Prize
    await Prize(class_id="cls1", title="A", visible=True, point_cost=10, created_by=str(teacher.id)).insert()
    await Prize(class_id="cls1", title="B", visible=False, point_cost=20, created_by=str(teacher.id)).insert()

    visible = await Prize.find(Prize.class_id == "cls1", Prize.visible == True).to_list()  # noqa: E712
    assert len(visible) == 1
    assert visible[0].title == "A"


async def test_update_prize_visibility(db, teacher):
    from gamification.prizes.models import Prize
    prize = Prize(class_id="cls1", title="X", visible=True, point_cost=0, created_by=str(teacher.id))
    await prize.insert()
    prize.visible = False
    await prize.save()

    refreshed = await Prize.get(prize.id)
    assert refreshed.visible is False


async def test_delete_prize(db, teacher):
    from gamification.prizes.models import Prize
    prize = Prize(class_id="cls1", title="Y", point_cost=0, created_by=str(teacher.id))
    await prize.insert()
    await prize.delete()
    assert await Prize.get(prize.id) is None


# ─── Router-level test: student visibility filter ────────────────────────────

@pytest.fixture
async def prizes_app(db):
    from core.users.models import User, IdentityTag
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT
    from fastapi import FastAPI
    from gamification.prizes.router import router as prizes_router

    student = User(
        username="stu_list",
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=int(STUDENT),
        identity_tags=[IdentityTag.STUDENT],
    )
    await student.insert()

    app = FastAPI()
    app.include_router(prizes_router)
    return app, student


async def test_student_list_prizes_returns_200(prizes_app):
    """Student calling list_prizes must return 200 and see only visible prizes.

    Bug (R7): user.role raises AttributeError — User uses identity_tags, not role.
    """
    from core.auth.jwt import create_access_token
    from core.auth.permissions import STUDENT
    from gamification.prizes.models import Prize

    app, student = prizes_app
    await Prize(class_id="cls1", title="Visible", visible=True, point_cost=10, created_by=str(student.id)).insert()
    await Prize(class_id="cls1", title="Hidden", visible=False, point_cost=20, created_by=str(student.id)).insert()

    token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        resp = await ac.get("/classes/cls1/prizes")
    assert resp.status_code == 200
    titles = [p["title"] for p in resp.json()]
    assert titles == ["Visible"]


# ═══════════════════════════════════════════════════════════════════════════
# add-prize-redemption — redeem endpoint, IDOR/permission, and page routes
# ═══════════════════════════════════════════════════════════════════════════


async def _make_redeem_db(db_name: str):
    """Init mongomock with the models the redeem endpoint touches."""
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from gamification.points.models import PointTransaction
    from gamification.prizes.models import Prize

    client = AsyncMongoMockClient()
    database = client.get_database(db_name)
    await init_beanie(
        database=database,
        document_models=[User, Class, ClassMembership, Prize, PointTransaction],
    )
    return client


def _redeem_app():
    """A bare app mounting only the prizes router (no template rendering needed)."""
    from fastapi import FastAPI
    from gamification.prizes.router import router as prizes_router

    app = FastAPI()
    app.include_router(prizes_router)
    return app


async def _seed_student(username: str, perms_int: int, member_class_id=None, balance: int = 0):
    """Create a student, optional class membership, and an opening balance ledger entry."""
    from core.auth.password import hash_password
    from core.classes.models import ClassMembership
    from core.users.models import IdentityTag, User
    from gamification.points.models import PointTransaction

    student = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=perms_int,
        identity_tags=[IdentityTag.STUDENT],
    )
    await student.insert()
    if member_class_id is not None:
        await ClassMembership(
            class_id=member_class_id, user_id=str(student.id), role="student"
        ).insert()
    if balance:
        await PointTransaction(
            student_id=str(student.id),
            class_id=member_class_id or "seed",
            amount=balance,
            reason="seed",
            source_event="checkin",
            source_id="seed",
            created_by="system",
        ).insert()
    return student


async def _post_redeem(app, student, class_id: str, prize_id: str):
    from core.auth.jwt import create_access_token
    from core.auth.permissions import STUDENT

    token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        return await ac.post(f"/classes/{class_id}/prizes/{prize_id}/redeem")


async def _count_redemptions():
    from gamification.points.models import PointTransaction

    return await PointTransaction.find(
        PointTransaction.source_event == "prize_redemption"
    ).to_list()


# ─── Task 1.1 — service aborts before insert on insufficient balance ─────────

async def test_redeem_service_aborts_without_insert_when_insufficient():
    client = await _make_redeem_db("test_redeem_svc_insufficient")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize
        from gamification.prizes.service import InsufficientPointsError, redeem_prize

        student = await _seed_student("svc_poor", int(STUDENT), member_class_id="clsS", balance=10)
        prize = Prize(class_id="clsS", title="P", visible=True, point_cost=99, created_by="t")
        await prize.insert()

        with pytest.raises(InsufficientPointsError):
            await redeem_prize(str(student.id), prize)

        assert await _count_redemptions() == []
    finally:
        client.close()


# ─── Task 4.1 — redeem success + insufficient balance ─────────────────────────

async def test_redeem_success_deducts_and_records_single_negative_tx():
    client = await _make_redeem_db("test_redeem_success")
    try:
        from core.auth.permissions import STUDENT
        from gamification.points.service import get_balance
        from gamification.prizes.models import Prize

        student = await _seed_student("redeem_ok", int(STUDENT), member_class_id="clsR", balance=100)
        prize = Prize(class_id="clsR", title="書券", visible=True, point_cost=30, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsR", str(prize.id))
        assert resp.status_code == 200, resp.text
        assert resp.json()["new_balance"] == 70
        assert await get_balance(str(student.id)) == 70

        redemptions = await _count_redemptions()
        assert len(redemptions) == 1
        assert redemptions[0].amount == -30
        assert redemptions[0].source_id == str(prize.id)
        assert redemptions[0].class_id == "clsR"
        assert redemptions[0].created_by == str(student.id)
    finally:
        client.close()


async def test_redeem_insufficient_balance_rejected_without_deduction():
    client = await _make_redeem_db("test_redeem_insufficient")
    try:
        from core.auth.permissions import STUDENT
        from gamification.points.service import get_balance
        from gamification.prizes.models import Prize

        student = await _seed_student("redeem_poor", int(STUDENT), member_class_id="clsR", balance=20)
        prize = Prize(class_id="clsR", title="貴", visible=True, point_cost=50, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsR", str(prize.id))
        assert 400 <= resp.status_code < 500, resp.text
        assert await get_balance(str(student.id)) == 20
        assert await _count_redemptions() == []
    finally:
        client.close()


# ─── Task 4.2 — non-member / invisible / cross-class redemption guards ─────────

async def test_redeem_non_member_forbidden():
    client = await _make_redeem_db("test_redeem_non_member")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize

        # Not a member of clsR, but has a global balance.
        student = await _seed_student("redeem_outsider", int(STUDENT), member_class_id=None, balance=100)
        prize = Prize(class_id="clsR", title="X", visible=True, point_cost=10, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsR", str(prize.id))
        assert resp.status_code == 403, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


async def test_redeem_invisible_prize_rejected():
    client = await _make_redeem_db("test_redeem_invisible")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize

        student = await _seed_student("redeem_inv", int(STUDENT), member_class_id="clsR", balance=100)
        prize = Prize(class_id="clsR", title="Hidden", visible=False, point_cost=10, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsR", str(prize.id))
        assert 400 <= resp.status_code < 500, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


async def test_redeem_cross_class_path_mismatch_rejected():
    client = await _make_redeem_db("test_redeem_cross_class")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize

        # Student is a member of clsA; prize lives in clsA, but the path says clsB.
        student = await _seed_student("redeem_xclass", int(STUDENT), member_class_id="clsA", balance=100)
        prize = Prize(class_id="clsA", title="A-prize", visible=True, point_cost=10, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsB", str(prize.id))
        assert 400 <= resp.status_code < 500, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


async def test_redeem_missing_prize_returns_404():
    client = await _make_redeem_db("test_redeem_missing")
    try:
        from core.auth.permissions import STUDENT

        student = await _seed_student("redeem_missing", int(STUDENT), member_class_id="clsR", balance=100)
        resp = await _post_redeem(_redeem_app(), student, "clsR", "651111111111111111111111")
        assert resp.status_code == 404, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


# ─── Task 4.3 — PATCH/DELETE ownership (cross-teacher IDOR) + permission ───────

async def _make_teacher(username: str, perms_int: int):
    from core.auth.password import hash_password
    from core.users.models import User

    teacher = User(
        username=username,
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=perms_int,
    )
    await teacher.insert()
    return teacher


async def test_patch_delete_prize_cross_teacher_forbidden():
    client = await _make_redeem_db("test_prize_cross_teacher")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import TEACHER
        from core.classes.models import Class, ClassMembership
        from gamification.prizes.models import Prize

        teacher_b = await _make_teacher("idor_b", int(TEACHER))
        cls = Class(name="B-class", description="", visibility="private",
                    owner_id=str(teacher_b.id), invite_code="IDOR01")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(teacher_b.id), role="teacher").insert()
        prize = Prize(class_id=str(cls.id), title="B-prize", visible=True, point_cost=10,
                      created_by=str(teacher_b.id))
        await prize.insert()

        # Teacher A holds MANAGE_TASKS but is NOT a teacher of B's class.
        teacher_a = await _make_teacher("idor_a", int(TEACHER))

        app = _redeem_app()
        token = create_access_token(user_id=str(teacher_a.id), permissions=int(TEACHER))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            patch_resp = await ac.patch(f"/prizes/{prize.id}", json={"visible": False})
            delete_resp = await ac.delete(f"/prizes/{prize.id}")

        assert patch_resp.status_code == 403, patch_resp.text
        assert delete_resp.status_code == 403, delete_resp.text
        refreshed = await Prize.get(prize.id)
        assert refreshed is not None and refreshed.visible is True
    finally:
        client.close()


async def test_patch_delete_prize_without_manage_tasks_forbidden():
    client = await _make_redeem_db("test_prize_missing_perm")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize

        # A user lacking MANAGE_TASKS (plain student permissions).
        student = await _seed_student("no_manage", int(STUDENT), member_class_id="clsR", balance=0)
        prize = Prize(class_id="clsR", title="P", visible=True, point_cost=10, created_by="t")
        await prize.insert()

        app = _redeem_app()
        token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            patch_resp = await ac.patch(f"/prizes/{prize.id}", json={"visible": False})
            delete_resp = await ac.delete(f"/prizes/{prize.id}")

        assert patch_resp.status_code == 403, patch_resp.text
        assert delete_resp.status_code == 403, delete_resp.text
    finally:
        client.close()


# ─── Task 2.1 — page routes (student list / teacher manage guard) ─────────────

async def _make_full_db(db_name: str):
    """Init mongomock with every model needed to render base.html + page context."""
    from core.classes.models import Class, ClassMembership
    from core.users.models import User
    from gamification.badges.models import BadgeAward, BadgeDefinition
    from gamification.points.models import ClassPointConfig, PointTransaction
    from gamification.prizes.models import Prize
    from tasks.checkin.models import CheckinConfig, CheckinRecord, DailyCheckinOverride
    from tasks.submissions.models import TaskSubmission
    from tasks.templates.models import TaskAssignment, TaskScheduleRule, TaskTemplate

    client = AsyncMongoMockClient()
    database = client.get_database(db_name)
    await init_beanie(
        database=database,
        document_models=[
            User, Class, ClassMembership,
            TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
            CheckinConfig, DailyCheckinOverride, CheckinRecord,
            PointTransaction, ClassPointConfig,
            BadgeDefinition, BadgeAward, Prize,
        ],
    )
    return client


def _make_full_app():
    from community.feed.router import router as feed_router
    from core.auth.router import router as auth_router
    from fastapi import FastAPI
    from gamification.badges.router import router as badges_router
    from gamification.leaderboard.router import router as leaderboard_router
    from gamification.points.router import router as points_router
    from gamification.prizes.router import router as prizes_router
    from pages.router import router as pages_router
    from tasks.checkin.router import router as checkin_router
    from tasks.submissions.router import router as submissions_router
    from tasks.templates.router import router as templates_router

    app = FastAPI()
    for r in [auth_router, pages_router, submissions_router,
              badges_router, leaderboard_router, points_router,
              feed_router, checkin_router, templates_router, prizes_router]:
        app.include_router(r)
    return app


async def test_student_prizes_page_lists_only_visible():
    client = await _make_full_db("test_prizes_page_student")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import STUDENT
        from core.classes.models import Class, ClassMembership
        from core.users.models import IdentityTag, User
        from core.auth.password import hash_password
        from gamification.prizes.models import Prize

        student = User(username="pp_s", hashed_password=hash_password("pw"), display_name="PP",
                       permissions=int(STUDENT), identity_tags=[IdentityTag.STUDENT])
        await student.insert()
        cls = Class(name="PPClass", description="", visibility="private", owner_id="o", invite_code="PP0001")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(student.id), role="student").insert()
        await Prize(class_id=str(cls.id), title="VisiblePrizeX", visible=True, point_cost=10, created_by="t").insert()
        await Prize(class_id=str(cls.id), title="HiddenPrizeY", visible=False, point_cost=20, created_by="t").insert()

        app = _make_full_app()
        token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                               cookies={"access_token": token}) as ac:
            resp = await ac.get(f"/pages/classes/{cls.id}/prizes", follow_redirects=False)
        assert resp.status_code == 200, resp.text[:400]
        assert "VisiblePrizeX".encode() in resp.content
        assert "HiddenPrizeY".encode() not in resp.content
    finally:
        client.close()


async def test_teacher_prizes_manage_page_renders_for_manager():
    client = await _make_full_db("test_prizes_manage_ok")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import TEACHER
        from core.classes.models import Class, ClassMembership
        from core.users.models import User
        from core.auth.password import hash_password
        from gamification.prizes.models import Prize

        teacher = User(username="mgr_ok", hashed_password=hash_password("pw"),
                       display_name="Mgr", permissions=int(TEACHER))
        await teacher.insert()
        cls = Class(name="MgrClass", description="", visibility="private",
                    owner_id=str(teacher.id), invite_code="MG0001")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()
        await Prize(class_id=str(cls.id), title="MgHidden", visible=False, point_cost=5, created_by=str(teacher.id)).insert()

        app = _make_full_app()
        token = create_access_token(user_id=str(teacher.id), permissions=int(TEACHER))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                               cookies={"access_token": token}) as ac:
            resp = await ac.get(f"/pages/classes/{cls.id}/prizes/manage", follow_redirects=False)
        assert resp.status_code == 200, resp.text[:400]
        # Hidden prizes are included on the management page.
        assert "MgHidden".encode() in resp.content
    finally:
        client.close()


async def test_teacher_prizes_manage_page_forbidden_for_non_manager():
    client = await _make_full_db("test_prizes_manage_forbidden")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import STUDENT
        from core.classes.models import Class
        from core.users.models import IdentityTag, User
        from core.auth.password import hash_password

        student = User(username="nm_mgr", hashed_password=hash_password("pw"), display_name="NM",
                       permissions=int(STUDENT), identity_tags=[IdentityTag.STUDENT])
        await student.insert()
        cls = Class(name="NMClass", description="", visibility="private", owner_id="o", invite_code="NM0001")
        await cls.insert()

        app = _make_full_app()
        token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                               cookies={"access_token": token}) as ac:
            resp = await ac.get(f"/pages/classes/{cls.id}/prizes/manage", follow_redirects=False)
        assert resp.status_code == 403, resp.text[:300]
    finally:
        client.close()


# ═══════════════════════════════════════════════════════════════════════════
# FIX round 1 — non-positive point_cost guard + page membership + redeem role
# ═══════════════════════════════════════════════════════════════════════════


# ─── Non-positive point_cost must never deduct, mint, or free-redeem ──────────

async def test_redeem_negative_cost_prize_rejected_without_minting():
    """A point_cost < 0 prize must be rejected — redemption must never ADD points."""
    client = await _make_redeem_db("test_redeem_negcost")
    try:
        from core.auth.permissions import STUDENT
        from gamification.points.service import get_balance
        from gamification.prizes.models import Prize

        student = await _seed_student("redeem_neg", int(STUDENT), member_class_id="clsN", balance=0)
        prize = Prize(class_id="clsN", title="MintBug", visible=True, point_cost=-100, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsN", str(prize.id))
        assert 400 <= resp.status_code < 500, resp.text
        # No minting: balance stays 0 and no redemption ledger entry is written.
        assert await get_balance(str(student.id)) == 0
        assert await _count_redemptions() == []
    finally:
        client.close()


async def test_redeem_zero_cost_prize_rejected():
    """A point_cost == 0 prize must be rejected — no unlimited free redemptions."""
    client = await _make_redeem_db("test_redeem_zerocost")
    try:
        from core.auth.permissions import STUDENT
        from gamification.points.service import get_balance
        from gamification.prizes.models import Prize

        student = await _seed_student("redeem_zero", int(STUDENT), member_class_id="clsZ", balance=50)
        prize = Prize(class_id="clsZ", title="FreeBug", visible=True, point_cost=0, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsZ", str(prize.id))
        assert 400 <= resp.status_code < 500, resp.text
        assert await get_balance(str(student.id)) == 50
        assert await _count_redemptions() == []
    finally:
        client.close()


async def test_redeem_service_rejects_non_positive_cost():
    """The service itself refuses non-positive cost and inserts nothing (defense-in-depth)."""
    client = await _make_redeem_db("test_redeem_svc_nonpositive")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize
        from gamification.prizes.service import redeem_prize

        student = await _seed_student("svc_np", int(STUDENT), member_class_id="clsP", balance=100)
        for bad_cost in (0, -25):
            prize = Prize(class_id="clsP", title="bad", visible=True, point_cost=bad_cost, created_by="t")
            await prize.insert()
            with pytest.raises(ValueError):
                await redeem_prize(str(student.id), prize)
        assert await _count_redemptions() == []
    finally:
        client.close()


# ─── Redemption is restricted to student-role members ────────────────────────

async def test_redeem_teacher_role_member_forbidden():
    """A teacher-role member of the class cannot redeem (兌換以 student member 為準)."""
    client = await _make_redeem_db("test_redeem_teacher_member")
    try:
        from core.auth.password import hash_password
        from core.auth.permissions import STUDENT
        from core.classes.models import ClassMembership
        from core.users.models import IdentityTag, User
        from gamification.points.models import PointTransaction
        from gamification.prizes.models import Prize

        u = User(username="tm_member", hashed_password=hash_password("pw"),
                 display_name="TM", permissions=int(STUDENT), identity_tags=[IdentityTag.STUDENT])
        await u.insert()
        await ClassMembership(class_id="clsT", user_id=str(u.id), role="teacher").insert()
        await PointTransaction(
            student_id=str(u.id), class_id="clsT", amount=100, reason="seed",
            source_event="checkin", source_id="seed", created_by="system",
        ).insert()
        prize = Prize(class_id="clsT", title="X", visible=True, point_cost=10, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), u, "clsT", str(prize.id))
        assert resp.status_code == 403, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


# ─── Student prizes page must enforce class membership ───────────────────────

async def test_student_prizes_page_non_member_forbidden():
    """A logged-in non-member cannot enumerate another class's visible prize catalog."""
    client = await _make_full_db("test_prizes_page_nonmember")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import STUDENT
        from core.classes.models import Class
        from core.users.models import IdentityTag, User
        from core.auth.password import hash_password
        from gamification.prizes.models import Prize

        student = User(username="pp_nm", hashed_password=hash_password("pw"), display_name="NM",
                       permissions=int(STUDENT), identity_tags=[IdentityTag.STUDENT])
        await student.insert()
        cls = Class(name="OtherClass", description="", visibility="private", owner_id="o", invite_code="OT0001")
        await cls.insert()
        # student is intentionally NOT a member of cls
        await Prize(class_id=str(cls.id), title="SecretPrize", visible=True, point_cost=10, created_by="t").insert()

        app = _make_full_app()
        token = create_access_token(user_id=str(student.id), permissions=int(STUDENT))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                               cookies={"access_token": token}) as ac:
            resp = await ac.get(f"/pages/classes/{cls.id}/prizes", follow_redirects=False)
        assert resp.status_code == 403, resp.text[:300]
        assert "SecretPrize".encode() not in resp.content
    finally:
        client.close()


# ═══════════════════════════════════════════════════════════════════════════
# FIX round 2 — create-side positive-cost guard + redeem membership-before-
# visibility ordering (no existence/visibility oracle for non-members)
# ═══════════════════════════════════════════════════════════════════════════


async def test_create_prize_rejects_non_positive_cost():
    """The create endpoint must refuse point_cost <= 0 so the teacher UI can never
    publish a prize the redeem rule (point_cost > 0) can never honour. No Prize
    document is inserted for the rejected request."""
    client = await _make_redeem_db("test_create_nonpositive_cost")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import TEACHER
        from core.classes.models import Class, ClassMembership
        from gamification.prizes.models import Prize

        teacher = await _make_teacher("create_guard", int(TEACHER))
        cls = Class(name="C-class", description="", visibility="private",
                    owner_id=str(teacher.id), invite_code="CGUARD")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()

        app = _redeem_app()
        token = create_access_token(user_id=str(teacher.id), permissions=int(TEACHER))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            zero_resp = await ac.post(f"/classes/{cls.id}/prizes",
                                      json={"title": "Zero", "point_cost": 0})
            neg_resp = await ac.post(f"/classes/{cls.id}/prizes",
                                     json={"title": "Neg", "point_cost": -5})

        assert 400 <= zero_resp.status_code < 500, zero_resp.text
        assert 400 <= neg_resp.status_code < 500, neg_resp.text
        # Nothing was inserted for either rejected request.
        assert await Prize.find(Prize.class_id == str(cls.id)).to_list() == []
    finally:
        client.close()


async def test_create_prize_accepts_positive_cost():
    """A positive point_cost still creates the prize (guard does not over-reject)."""
    client = await _make_redeem_db("test_create_positive_cost")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import TEACHER
        from core.classes.models import Class, ClassMembership
        from gamification.prizes.models import Prize

        teacher = await _make_teacher("create_ok", int(TEACHER))
        cls = Class(name="C2-class", description="", visibility="private",
                    owner_id=str(teacher.id), invite_code="CGOOD0")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()

        app = _redeem_app()
        token = create_access_token(user_id=str(teacher.id), permissions=int(TEACHER))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            resp = await ac.post(f"/classes/{cls.id}/prizes",
                                 json={"title": "Good", "point_cost": 25})

        assert resp.status_code == 201, resp.text
        prizes = await Prize.find(Prize.class_id == str(cls.id)).to_list()
        assert len(prizes) == 1 and prizes[0].point_cost == 25
    finally:
        client.close()


async def test_patch_prize_rejects_non_positive_cost():
    """PATCH must also refuse point_cost <= 0 so an existing prize cannot be
    edited into an unredeemable zero/negative-cost state."""
    client = await _make_redeem_db("test_patch_nonpositive_cost")
    try:
        from core.auth.jwt import create_access_token
        from core.auth.permissions import TEACHER
        from core.classes.models import Class, ClassMembership
        from gamification.prizes.models import Prize

        teacher = await _make_teacher("patch_guard", int(TEACHER))
        cls = Class(name="P-class", description="", visibility="private",
                    owner_id=str(teacher.id), invite_code="PGUARD")
        await cls.insert()
        await ClassMembership(class_id=str(cls.id), user_id=str(teacher.id), role="teacher").insert()
        prize = Prize(class_id=str(cls.id), title="P", visible=True, point_cost=30,
                      created_by=str(teacher.id))
        await prize.insert()

        app = _redeem_app()
        token = create_access_token(user_id=str(teacher.id), permissions=int(TEACHER))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("access_token", token)
            resp = await ac.patch(f"/prizes/{prize.id}", json={"point_cost": 0})

        assert 400 <= resp.status_code < 500, resp.text
        refreshed = await Prize.get(prize.id)
        assert refreshed.point_cost == 30  # unchanged
    finally:
        client.close()


async def test_redeem_non_member_invisible_prize_returns_403():
    """Membership is checked BEFORE visibility: a non-member redeeming an INVISIBLE
    prize must get the same 403 as for a visible prize, so visibility is never
    leaked to non-members via a 400-vs-403 oracle."""
    client = await _make_redeem_db("test_redeem_nonmember_invisible")
    try:
        from core.auth.permissions import STUDENT
        from gamification.prizes.models import Prize

        # Not a member of clsR, but has a global balance.
        student = await _seed_student("nm_invis", int(STUDENT), member_class_id=None, balance=100)
        prize = Prize(class_id="clsR", title="HiddenSecret", visible=False, point_cost=10, created_by="t")
        await prize.insert()

        resp = await _post_redeem(_redeem_app(), student, "clsR", str(prize.id))
        assert resp.status_code == 403, resp.text
        assert await _count_redemptions() == []
    finally:
        client.close()


# ═══════════════════════════════════════════════════════════════════════════
# FIX round 3 — dashboard prize links are guarded against silent route renames
# ═══════════════════════════════════════════════════════════════════════════
#
# The student/dashboard.html nav links to the prize pages are written as literal
# paths (not url_for): the dashboard is rendered by page-render test apps that do
# NOT mount the prizes router, where url_for('prizes_page'/'prizes_manage_page')
# would raise NoMatchFound. The trade-off is that a literal path could drift out
# of sync if the route path in router.py were renamed. This test closes that gap:
# it derives the live route paths from the prizes router and asserts the dashboard
# still contains a matching href, so a route rename now fails a test instead of
# breaking the links silently.


def _dashboard_href_regex(route_path: str):
    """Turn a FastAPI route path into a regex matching the dashboard href literal.

    e.g. ``/pages/classes/{class_id}/prizes`` →
         ``href="/pages/classes/{{ <jinja expr> }}/prizes"``
    The ``{class_id}`` path param maps to a Jinja expression ``{{ ... }}`` and the
    trailing ``"`` anchors the end so the student ``/prizes`` link is not satisfied
    by the longer teacher ``/prizes/manage`` link (and vice versa).
    """
    import re

    parts = re.split(r"\{[^}]+\}", route_path)
    jinja_param = r"\{\{\s*[\w.]+\s*\}\}"
    escaped = jinja_param.join(re.escape(p) for p in parts)
    return re.compile(r'href="' + escaped + r'"')


def test_dashboard_prize_links_match_live_routes():
    """The dashboard's literal prize links must stay in sync with the live routes.

    If someone renames the prize page route paths in router.py, these assertions
    fail — the dashboard nav links can no longer break silently (finding PRIZE-2).
    """
    from pathlib import Path

    from gamification.prizes.router import router as prizes_router

    paths = {
        r.name: r.path
        for r in prizes_router.routes
        if getattr(r, "name", None) in ("prizes_page", "prizes_manage_page")
    }
    assert set(paths) == {"prizes_page", "prizes_manage_page"}, (
        "Expected named prize page routes 'prizes_page' and 'prizes_manage_page'; "
        f"found {sorted(paths)}"
    )

    dashboard = (
        Path(__file__).parent.parent
        / "src" / "templates" / "student" / "dashboard.html"
    ).read_text(encoding="utf-8")

    for name, path in paths.items():
        rx = _dashboard_href_regex(path)
        assert rx.search(dashboard), (
            f"student/dashboard.html has no href matching live route {name!r} "
            f"({path!r}); the literal link drifted out of sync with router.py"
        )


# ═══════════════════════════════════════════════════════════════════════════
# FIX round 4 — sequential double-spend (no-duplicate-redemption) acceptance
# ═══════════════════════════════════════════════════════════════════════════
#
# Handoff §5 BUILD acceptance lists 「無重複兌換」(no-duplicate-redemption). The
# first redemption drains the balance to exactly 0 via its own deduction ledger
# entry; because get_balance re-reads that entry, the second redemption of the
# SAME prize must be rejected with a 4xx insufficient-points and must NOT write a
# second deduction. This exercises the sequential double-spend path end-to-end
# (the earlier tests only cover a single redeem and a pre-seeded low balance).


async def test_redeem_twice_second_rejected_no_double_spend():
    client = await _make_redeem_db("test_redeem_double_spend")
    try:
        from core.auth.permissions import STUDENT
        from gamification.points.service import get_balance
        from gamification.prizes.models import Prize

        # Balance == point_cost: enough for exactly one redemption, not two.
        student = await _seed_student("redeem_twice", int(STUDENT), member_class_id="clsD", balance=30)
        prize = Prize(class_id="clsD", title="書券", visible=True, point_cost=30, created_by="t")
        await prize.insert()

        app = _redeem_app()

        # First redemption succeeds and drains the balance to exactly 0.
        first = await _post_redeem(app, student, "clsD", str(prize.id))
        assert first.status_code == 200, first.text
        assert first.json()["new_balance"] == 0
        assert await get_balance(str(student.id)) == 0
        after_first = await _count_redemptions()
        assert len(after_first) == 1
        assert after_first[0].amount == -30
        assert after_first[0].source_id == str(prize.id)

        # Second redemption of the SAME prize is rejected: balance is now 0 < 30.
        second = await _post_redeem(app, student, "clsD", str(prize.id))
        assert 400 <= second.status_code < 500, second.text
        # No double-spend: ledger and balance are unchanged after the rejection.
        assert await get_balance(str(student.id)) == 0
        assert len(await _count_redemptions()) == 1
    finally:
        client.close()
