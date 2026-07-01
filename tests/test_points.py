"""Tests for points-system capability."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_points")
    from core.users.models import User
    from core.classes.models import Class
    from gamification.points.models import PointTransaction, ClassPointConfig
    await init_beanie(
        database=database,
        document_models=[User, Class, PointTransaction, ClassPointConfig],
    )
    yield database
    client.close()


@pytest.fixture
async def student(db):
    from core.users.models import User
    from core.auth.password import hash_password
    u = User(username="stu", hashed_password=hash_password("pw"), display_name="S", role="student")
    await u.insert()
    return u


# --- Balance ---

async def test_balance_starts_at_zero(db, student):
    from gamification.points.service import get_balance
    balance = await get_balance(str(student.id))
    assert balance == 0


async def test_balance_reflects_transactions(db, student):
    from gamification.points.service import award_points, get_balance
    await award_points(str(student.id), "cls1", 10, "checkin", "evt1")
    await award_points(str(student.id), "cls1", 5, "submission", "evt2")
    assert await get_balance(str(student.id)) == 15


async def test_get_class_balance_is_class_scoped(db, student):
    """get_class_balance counts only the given class's transactions (FINDING-002)."""
    from gamification.points.service import award_points, get_balance, get_class_balance
    await award_points(str(student.id), "clsA", 10, "checkin", "evtA")
    await award_points(str(student.id), "clsB", 5, "checkin", "evtB")
    # Global balance still sums across classes …
    assert await get_balance(str(student.id)) == 15
    # … but the class-scoped balance is isolated per class.
    assert await get_class_balance(str(student.id), "clsA") == 10
    assert await get_class_balance(str(student.id), "clsB") == 5


# --- Award ---

async def test_award_points_creates_transaction(db, student):
    from gamification.points.service import award_points, get_transaction_history
    await award_points(str(student.id), "cls1", 10, "checkin", "evt1")
    history = await get_transaction_history(str(student.id))
    assert len(history) == 1
    assert history[0].amount == 10


# --- Revoke ---

async def test_revoke_points_creates_negative_transaction(db, student):
    from gamification.points.service import award_points, revoke_points, get_balance
    await award_points(str(student.id), "cls1", 20, "checkin", "evt1")
    await revoke_points(str(student.id), "cls1", 8, "penalty", "teacher1")
    assert await get_balance(str(student.id)) == 12


async def test_revoke_capped_at_current_balance(db, student):
    from gamification.points.service import award_points, revoke_points, get_balance
    await award_points(str(student.id), "cls1", 5, "checkin", "evt1")
    # Try to revoke 100 but only 5 available
    await revoke_points(str(student.id), "cls1", 100, "penalty", "teacher1")
    assert await get_balance(str(student.id)) == 0


# --- CheckinRewardProvider ---

async def test_checkin_reward_provider_awards_points(db, student):
    from gamification.points.models import ClassPointConfig
    from gamification.points.providers import CheckinRewardProvider
    from extensions.protocols.reward import RewardEvent, RewardEventType

    # Set config: 5 points per checkin
    config = ClassPointConfig(class_id="cls1", checkin_points=5, submission_points=10)
    await config.insert()

    provider = CheckinRewardProvider()
    event = RewardEvent(
        event_type=RewardEventType.CHECKIN,
        student_id=str(student.id),
        class_id="cls1",
        source_id="record1",
    )
    tx = await provider.award(event)
    assert tx is not None
    assert tx.amount == 5


async def test_submission_reward_provider_awards_points(db, student):
    from gamification.points.models import ClassPointConfig
    from gamification.points.providers import SubmissionRewardProvider
    from extensions.protocols.reward import RewardEvent, RewardEventType

    config = ClassPointConfig(class_id="cls1", checkin_points=5, submission_points=10)
    await config.insert()

    provider = SubmissionRewardProvider()
    event = RewardEvent(
        event_type=RewardEventType.SUBMISSION,
        student_id=str(student.id),
        class_id="cls1",
        source_id="sub1",
    )
    tx = await provider.award(event)
    assert tx is not None
    assert tx.amount == 10


# --- Teacher deduct (teacher_deduct entry type) ---

async def test_teacher_deduct_creates_negative_transaction(db, student):
    """Teacher deduct creates a PointTransaction with source_event='teacher_deduct' (task 2.1)."""
    from gamification.points.service import award_points, deduct_points, get_balance
    await award_points(str(student.id), "cls1", 20, "submission", "evt1")
    tx = await deduct_points(
        student_id=str(student.id),
        class_id="cls1",
        amount=5,
        reason="誤用積分",
        deducted_by="teacher1",
    )
    assert tx.amount == -5
    assert tx.source_event == "teacher_deduct"
    assert tx.reason == "誤用積分"


async def test_teacher_deduct_balance_reflects_deduction(db, student):
    """Student balance reflects teacher_deduct transaction (task 2.3)."""
    from gamification.points.service import award_points, deduct_points, get_balance
    await award_points(str(student.id), "cls1", 30, "submission", "evt1")
    await deduct_points(str(student.id), "cls1", 10, "penalty", "teacher1")
    assert await get_balance(str(student.id)) == 20


async def test_teacher_deduct_not_capped_at_balance(db, student):
    """Teacher deduct does not cap at current balance (unlike revoke_points)."""
    from gamification.points.service import award_points, deduct_points, get_balance
    await award_points(str(student.id), "cls1", 5, "submission", "evt1")
    tx = await deduct_points(str(student.id), "cls1", 100, "over-deduct", "teacher1")
    assert tx.amount == -100
    # Balance can go negative
    assert await get_balance(str(student.id)) == -95
