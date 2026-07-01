## Why

The pre-1.0.0 adversarial review found that `GET /classes/{class_id}/prizes` (`list_prizes`) performed no class-scoped authorization: any authenticated user could enumerate another class's prizes, and a non-student caller even received invisible prizes (CWE-200). This is the same class of cross-class disclosure as the audit findings and must be closed before release.

## What Changes

- `list_prizes` now requires class-scoped authorization: load the class (404 if absent); managing teachers (`can_manage_class`) see all prizes; class members see only `visible` prizes; non-members receive HTTP 403.

## Non-Goals

- Visibility semantics for members are unchanged (members still see only `visible` prizes); only the missing membership/manager gate is added.
- The two other out-of-scope siblings surfaced by the review (`checkin_status` timing metadata; schedule/assign template↔class integrity) are deferred to a later release.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `prize-preview`: prize listing enforces class-scoped authorization.

## Impact

- Code: `src/gamification/prizes/router.py`.
- Tests: `tests/test_prizes.py` (fixture upgraded to a real class + members; member/non-member/manager cases).
- Behavior: non-members now receive 403 on the prize listing endpoint; the `IdentityTag`-based visibility switch is replaced by a manager-vs-member decision.
