---
id: FINDING-002
title: "Class leaderboards use cross-class point totals"
severity: Medium
cwe: CWE-200
status: open
---

## Description

Class-scoped leaderboard and points-management logic call `get_balance(student_id)` and `get_transaction_history(student_id)` helpers that ignore `class_id` entirely. As a result, pages and APIs that are supposed to represent one class operate on a student's aggregate balance across every class they belong to. This contradicts the class-scoped transaction model (`PointTransaction` stores `class_id`) and weakens class isolation because one class's UI reveals or acts on points earned elsewhere.

## Evidence

- **File**: `src/gamification/points/service.py:5`
- **Code**:
  ```
  async def get_balance(student_id: str) -> int:
      transactions = await PointTransaction.find(
          PointTransaction.student_id == student_id
      ).to_list()
      return sum(t.amount for t in transactions)

  async def get_transaction_history(student_id: str) -> list[PointTransaction]:
      return await PointTransaction.find(
          PointTransaction.student_id == student_id
      ).sort(-PointTransaction.created_at).to_list()
  ```
- **Explanation**: Both helpers aggregate across all transactions for the student, even though each transaction already records a `class_id`. No class-scoped variant exists.

- **File**: `src/gamification/leaderboard/router.py:16`
- **Code**:
  ```
  async def _build_class_leaderboard(class_id: str) -> list[dict]:
      memberships = await ClassMembership.find(
          ClassMembership.class_id == class_id,
          ClassMembership.role == "student",
      ).to_list()
      ...
      for m in memberships:
          user = await User.get(m.user_id)
          balance = await get_balance(m.user_id)
          entries.append({"student_id": m.user_id, "display_name": user.display_name if user else m.user_id, "points": balance})
  ```
- **Explanation**: The class leaderboard ranks students using their global balance, not the balance of transactions belonging to `class_id`.

- **File**: `src/gamification/points/service.py:63`
- **Code**:
  ```
  async def revoke_points(...):
      current_balance = await get_balance(student_id)
      capped_amount = min(amount, current_balance)
      tx = PointTransaction(
          student_id=student_id,
          class_id=class_id,
          amount=-capped_amount,
          ...
      )
  ```
- **Explanation**: The per-class revoke flow is capped against the student's global balance, so a teacher in one class can deduct value backed by points earned in a different class.

## Impact

Teachers and students viewing a class-scoped leaderboard or points page can infer a student's activity in other classes from inflated balances. A teacher's revoke action in one class can also reduce value effectively backed by points from another class, creating cross-class interference. Beyond the privacy issue, this diverges from the OpenSpec requirement that each class have its own leaderboard behavior.

## Remediation

### Recommendation

Introduce class-aware balance/history helpers that filter `PointTransaction` by both `student_id` and `class_id`, then use them everywhere a class-scoped page, API, or revocation flow is expected to operate within one class. Keep the current global helper only for explicitly cross-class features such as the aggregate leaderboard or global dashboard totals.

### Before

```
balance = await get_balance(m.user_id)
```

### After

```
balance = await get_class_balance(student_id=m.user_id, class_id=class_id)
```

### References

- [CWE-200](https://cwe.mitre.org/data/definitions/200.html)
