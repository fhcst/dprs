## Why

A pre-release security audit (2026-04-02) left four findings open in the release candidate. Three are class-scoped authorization gaps — cross-class read of student data, a leaderboard page that bypasses class membership, and leaderboards/revoke-caps drawing on cross-class point totals — and one is an input-validation gap where a malformed schedule rule is persisted and then crashes expansion. FINDING-001 in particular is systemic: the same missing check spans several teacher-facing routes (submission review, attendance, template, and points-management pages), not a single endpoint. Tagging v1.0.0 with these open would release known authorization and validation defects affecting student data across classes.

## What Changes

- Enforce class management (`can_manage_class`) on every teacher route that returns another class's data: the submissions listing endpoint and review page, the attendance page, the template list/new/edit/assign pages, and the points-management page (FINDING-001, CWE-639).
- Compute point balances scoped to a single class; leaderboards, the points page, and revoke caps no longer include points earned in other classes (FINDING-002, CWE-200).
- Enforce class membership on the leaderboard HTML page, mirroring the API route (FINDING-003, CWE-862).
- Validate schedule-rule requests (bounded `schedule_type` + mode-specific required date fields), rejecting malformed input with HTTP 422 before any persistence (FINDING-004, CWE-20).
- Add regression tests covering each finding and each newly-guarded route.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `task-submissions`: teacher submission listing endpoint and review page require class management.
- `checkin`: attendance page requires class management.
- `task-templates`: teacher template pages require class management on the derived class.
- `points-system`: adds class-scoped balance; points-management page requires class management and shows class-scoped balances.
- `leaderboard`: page route enforces class membership, and rankings reflect class-scoped point totals.
- `task-schedule-rule`: schedule-rule requests are validated before persistence.

## Impact

- Code: `src/tasks/submissions/router.py`, `src/tasks/checkin/router.py`, `src/tasks/templates/router.py`, `src/gamification/points/service.py`, `src/gamification/points/router.py`, `src/gamification/leaderboard/router.py`.
- Tests: `tests/test_cross_class_submissions.py`, `tests/test_cross_class_leaderboard.py`, `tests/test_cross_class_page_authz.py` (new), `tests/test_points.py`, `tests/test_schedule_rule_validation.py` (new), `tests/test_task_scheduling.py` (fixture corrected).
- Behavior: some previously-permitted cross-class reads now return 403; malformed schedule rules now return 422. No schema or migration changes.
