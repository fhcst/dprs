## Context

Four findings from the 2026-04-02 security audit remain open in the release candidate. The codebase already provides the primitives needed to close them — `can_manage_class()` / `_require_class_manage()` / `_require_template_class()` for class-scoped authorization, `ClassMembership` for membership checks, and Pydantic model validation for request hardening — so each fix reuses the established pattern rather than introducing new machinery. FINDING-001 turned out to be systemic: an enumeration of every teacher route taking a `class_id`/`template_id` found several page routes still gating on the coarse permission flag only.

## Goals / Non-Goals

**Goals**
- Close FINDING-001/002/003/004 with minimal, pattern-consistent changes.
- Close FINDING-001 across ALL affected teacher routes, not just the one endpoint the audit quoted first.
- Add a regression test per finding and per newly-guarded route so the audit cannot silently reopen.

**Non-Goals**
- No history rewrite of the already-public `.security-audit/` exposure (handled separately: tip removed, history retained by decision).
- No refactor of the wider authorization model; only the specific gap sites are touched.
- No change to intentionally-global semantics: the public cross-class leaderboard aggregate and a student's own `my_points` total continue to use the unscoped `get_balance()`.

## Decisions

### Teacher submission routes enforce class management

The submissions listing endpoint (`GET /classes/{class_id}/submissions`) and the review page (`GET /pages/teacher/class/{class_id}/submissions`) gated only on `MANAGE_TASKS`. Both now load the class and call `can_manage_class(teacher, cls)`, returning 403 otherwise — identical to the sibling approve/reject/comment endpoints.

### Attendance page enforces class management

`attendance_manage_page` checked only the coarse `MANAGE_OWN_CLASS | MANAGE_ALL_CLASSES` flag. It now additionally calls `can_manage_class()` on the target class, matching the API-side attendance-correction endpoint.

### Teacher template pages enforce class management

`templates_list_page` and `template_form_page` now call `_require_class_manage(class_id, teacher)`; `template_edit_page` and `template_assign_page` (keyed by `template_id`) now call `_require_template_class(template_id, teacher)`, which resolves the template's class and checks `can_manage_class()`. This matches the already-guarded template mutation endpoints.

### Class-scoped point balance

Points are earned per class, but `get_balance(student_id)` summed every class. A new `get_class_balance(student_id, class_id)` filters on both fields. `revoke_points()` caps against the class-scoped balance, and the points-management page displays class-scoped balances. The unscoped `get_balance()` is retained for the intentionally global cross-class leaderboard aggregate and the student's own points total.

### Points management page enforces class management

`points_manage_page` gated only on `MANAGE_TASKS` and exposed global balances. It now calls `can_manage_class()` on the class and builds member rows from `get_class_balance()`.

### Leaderboard page enforces class membership

The leaderboard HTML page computed visibility from a permission flag only. It now applies the same membership gate as the API route: unless the caller holds `MANAGE_ALL_CLASSES`, a `ClassMembership` in the class is required or the request returns 403.

### Leaderboard reflects class-scoped points

`_build_class_leaderboard(class_id)` used the global balance, exposing points earned in other classes. It now uses `get_class_balance(user_id, class_id)`.

### Schedule rule request validation

`ScheduleRuleRequest.schedule_type` was an unbounded `str` and date fields were all optional, so a malformed rule was persisted and then crashed `expand_schedule_rule()`. `schedule_type` is now `Literal["once","range","open"]` and a `model_validator(mode="after")` enforces the mode-specific required dates (and `end_date >= start_date`, `weekdays` in 0–6). Invalid requests are rejected with HTTP 422 at parse time, before the endpoint body runs — strictly stronger than reordering `insert()` after expansion, because nothing malformed is ever written.
