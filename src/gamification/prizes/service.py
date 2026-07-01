"""Prize redemption service.

Redemption is recorded as a single negative entry in the append-only point
ledger (``PointTransaction``) — the ledger entry *is* the redemption record, so
no separate collection is introduced. Balance is always the sum of a student's
transactions (see ``points.service.get_balance``).
"""
from gamification.points.models import PointTransaction
from gamification.points.service import get_balance
from gamification.prizes.models import Prize


class InsufficientPointsError(Exception):
    """Raised when a student's balance is below the prize's point cost."""


async def redeem_prize(student_id: str, prize: Prize) -> tuple[PointTransaction, int]:
    """Deduct ``prize.point_cost`` from ``student_id`` and record the redemption.

    Authorization precondition (caller's responsibility): this helper performs
    *no* membership, visibility, or class-scope checks. The caller MUST have
    already verified that ``student_id`` is a student-role member of
    ``prize.class_id`` and that ``prize.visible`` is true — the redeem endpoint in
    ``prizes.router`` enforces this before calling. Like
    ``points.service.revoke_points``, this function accepts a bare ``student_id``
    and only re-checks ``point_cost > 0`` and sufficient balance; reusing it from
    an unguarded path would bypass redemption authorization.

    Immediately before inserting the deduction, the current balance is
    re-checked against ``point_cost`` (the same TOCTOU mitigation used by
    ``points.service.revoke_points``). On a standalone MongoDB there is no
    multi-document transaction, so a residual TOCTOU window remains and is an
    accepted limitation consistent with the existing ledger design.

    Returns ``(transaction, new_balance)``. Raises ``InsufficientPointsError``
    without inserting anything when the balance is insufficient, and
    ``ValueError`` when ``point_cost`` is not strictly positive (a non-positive
    cost would otherwise mint points or allow unlimited free redemptions).
    """
    if prize.point_cost <= 0:
        # A non-positive cost is never redeemable: ``amount=-point_cost`` would
        # be >= 0, crediting (or no-op) instead of deducting. Refuse before any
        # balance read so no transaction can ever be inserted.
        raise ValueError(f"point_cost must be positive, got {prize.point_cost}")

    balance = await get_balance(student_id)
    if balance < prize.point_cost:
        raise InsufficientPointsError(
            f"balance {balance} < point_cost {prize.point_cost}"
        )

    tx = PointTransaction(
        student_id=student_id,
        class_id=prize.class_id,
        amount=-prize.point_cost,
        reason=f"兌換獎品：{prize.title}",
        source_event="prize_redemption",
        source_id=str(prize.id),
        created_by=student_id,
    )
    await tx.insert()

    new_balance = await get_balance(student_id)
    return tx, new_balance
