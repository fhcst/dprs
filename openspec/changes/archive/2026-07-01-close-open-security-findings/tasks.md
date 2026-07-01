# Tasks

## FINDING-001 (CWE-639) — systemic class-scoped authorization

- [x] Implement **Teacher submission routes enforce class management**: add `can_manage_class()` to `class_submissions` and `submission_review_page` (`src/tasks/submissions/router.py`)
- [x] Implement **Attendance page enforces class management**: add `can_manage_class()` to `attendance_manage_page` (`src/tasks/checkin/router.py`)
- [x] Implement **Teacher template pages enforce class management**: guard `templates_list_page`, `template_form_page` (`_require_class_manage`) and `template_edit_page`, `template_assign_page` (`_require_template_class`) (`src/tasks/templates/router.py`)
- [x] Implement **Points management page enforces class management**: add `can_manage_class()` to `points_manage_page` (`src/gamification/points/router.py`)
- [x] Regression tests for **Teacher submission routes enforce class management** and the page routes above: non-managing teacher → 403 (`tests/test_cross_class_submissions.py`, `tests/test_cross_class_page_authz.py`)
- [x] Repair the pre-existing `test_template_assign_page_returns_200` fixture (add teacher `ClassMembership`; register nav routers) so the positive path stays green (`tests/test_task_scheduling.py`)

## FINDING-002 (CWE-200) — class-scoped points

- [x] Implement **Class-scoped point balance**: add `get_class_balance(student_id, class_id)` and cap `revoke_points()` against it (`src/gamification/points/service.py`)
- [x] Implement **Points management page enforces class management** balance half: points page builds rows from `get_class_balance` (`src/gamification/points/router.py`)
- [x] Implement **Leaderboard reflects class-scoped points**: build `_build_class_leaderboard` from `get_class_balance(user_id, class_id)` (`src/gamification/leaderboard/router.py`)
- [x] Close **Class-scoped point balance** residual (adversarial review): `deduct_student_points` and `revoke_student_points` return `get_class_balance(...)` in their JSON `new_balance`, not the global total (`src/gamification/points/router.py`)
- [x] Regression tests for **Class-scoped point balance**: unit scoping (`tests/test_points.py`) + HTTP deduct-response is class-scoped (`tests/test_cross_class_gamification.py`)

## FINDING-003 (CWE-862) — leaderboard page membership

- [x] Implement **Leaderboard page enforces class membership**: mirror the API route's `ClassMembership` gate in `leaderboard_page` (`src/gamification/leaderboard/router.py`)
- [x] Regression test for **Leaderboard page enforces class membership** (`tests/test_cross_class_leaderboard.py`)

## FINDING-004 (CWE-20) — schedule rule validation

- [x] Implement **Schedule rule request validation**: constrain `schedule_type` to `Literal` and add a `model_validator` enforcing mode-specific date fields (`src/tasks/templates/router.py`)
- [x] Regression tests for **Schedule rule request validation** (`tests/test_schedule_rule_validation.py`)

## Verification

- [x] Full test suite green — 613 passed, 2 skipped (`.venv/bin/python -m pytest`)
- [x] `spectra validate --strict` and `analyze` clean (0 gaps)
- [x] Sonnet adversarial verification of the fixes — all 4 findings CLOSED after the FINDING-002 residual fix; no missed teacher routes within scope
