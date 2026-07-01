"""Points service functions."""
from gamification.points.models import PointTransaction


async def get_balance(student_id: str) -> int:
    """Compute balance by summing all transactions for the student (all classes)."""
    transactions = await PointTransaction.find(
        PointTransaction.student_id == student_id
    ).to_list()
    return sum(t.amount for t in transactions)


async def get_class_balance(student_id: str, class_id: str) -> int:
    """Compute a student's point balance scoped to a single class.

    Points are earned per class; class-facing surfaces (leaderboards, revoke
    caps) must not draw on totals accumulated in other classes.
    """
    transactions = await PointTransaction.find(
        PointTransaction.student_id == student_id,
        PointTransaction.class_id == class_id,
    ).to_list()
    return sum(t.amount for t in transactions)


async def get_transaction_history(student_id: str) -> list[PointTransaction]:
    """Return all transactions for a student in reverse chronological order."""
    return await PointTransaction.find(
        PointTransaction.student_id == student_id
    ).sort(-PointTransaction.created_at).to_list()


async def award_points(
    student_id: str,
    class_id: str,
    amount: int,
    source_event: str,
    source_id: str,
    created_by: str = "system",
) -> PointTransaction:
    """Create a positive point transaction."""
    tx = PointTransaction(
        student_id=student_id,
        class_id=class_id,
        amount=amount,
        reason=source_event,
        source_event=source_event,
        source_id=source_id,
        created_by=created_by,
    )
    await tx.insert()
    return tx


async def deduct_points(
    student_id: str,
    class_id: str,
    amount: int,
    reason: str,
    deducted_by: str,
) -> PointTransaction:
    """Deduct points from a student via teacher action (not capped)."""
    tx = PointTransaction(
        student_id=student_id,
        class_id=class_id,
        amount=-amount,
        reason=reason,
        source_event="teacher_deduct",
        source_id="",
        created_by=deducted_by,
    )
    await tx.insert()
    return tx


async def revoke_points(
    student_id: str,
    class_id: str,
    amount: int,
    reason: str,
    revoked_by: str,
) -> PointTransaction:
    """
    Deduct points from a student.
    The deduction is capped at the student's current balance in this class.
    """
    current_balance = await get_class_balance(student_id, class_id)
    capped_amount = min(amount, current_balance)

    tx = PointTransaction(
        student_id=student_id,
        class_id=class_id,
        amount=-capped_amount,
        reason=reason,
        source_event="manual_revoke",
        source_id="",
        created_by=revoked_by,
    )
    await tx.insert()
    return tx
