# task-templates Specification

## Purpose

TBD - created by archiving change 'daily-training-submission-system'. Update Purpose after archive.

## Requirements

### Requirement: Teacher creates a task template

Teachers SHALL be able to create a task template for a class. A template MUST include a title, optional description, and one or more field definitions. Each field definition MUST specify: name, field type (text, markdown, number, checkbox), and whether it is required.

#### Scenario: Template with multiple fields created

- **WHEN** a teacher submits a template with a title and at least one field definition
- **THEN** the system SHALL persist the template and associate it with the specified class

#### Scenario: Template with no fields rejected

- **WHEN** a teacher submits a template with zero field definitions
- **THEN** the system SHALL return a validation error and SHALL NOT persist the template


<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
code:
  - src/gamification/__init__.py
  - src/core/classes/router.py
  - src/core/classes/service.py
  - scripts/__init__.py
  - src/extensions/protocols/reward.py
  - src/extensions/registry/__init__.py
  - src/extensions/protocols/__init__.py
  - src/tasks/checkin/router.py
  - src/templates/teacher/templates_list.html
  - LICENSE
  - uv.lock
  - src/core/users/__init__.py
  - src/gamification/points/service.py
  - src/templates/community/leaderboard.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_form.html
  - src/core/auth/__init__.py
  - src/tasks/templates/models.py
  - src/templates/teacher/points_manage.html
  - src/templates/community/feed.html
  - src/community/feed/router.py
  - src/extensions/protocols/validator.py
  - src/shared/database.py
  - src/core/classes/__init__.py
  - src/tasks/checkin/service.py
  - src/tasks/templates/service.py
  - src/gamification/badges/__init__.py
  - src/gamification/points/models.py
  - src/tasks/checkin/__init__.py
  - src/community/feed/__init__.py
  - src/gamification/prizes/__init__.py
  - src/core/auth/deps.py
  - src/core/auth/jwt.py
  - src/extensions/deps.py
  - docker-compose.yml
  - src/community/__init__.py
  - src/core/auth/local_provider.py
  - src/core/classes/models.py
  - src/gamification/badges/router.py
  - src/gamification/leaderboard/router.py
  - scripts/migrations/__init__.py
  - src/gamification/points/router.py
  - src/main.py
  - src/extensions/registry/core.py
  - src/shared/__init__.py
  - src/tasks/checkin/models.py
  - src/core/users/router.py
  - pytest.ini
  - scripts/migrations/20260317_001_initial_indexes.py
  - src/tasks/submissions/__init__.py
  - src/community/feed/models.py
  - src/core/users/models.py
  - src/gamification/leaderboard/__init__.py
  - src/templates/student/badges.html
  - src/tasks/templates/router.py
  - src/gamification/points/providers.py
  - src/templates/student/dashboard.html
  - src/extensions/protocols/badge.py
  - src/tasks/templates/__init__.py
  - src/core/auth/password.py
  - src/extensions/__init__.py
  - src/gamification/points/__init__.py
  - pyproject.toml
  - src/extensions/protocols/auth.py
  - src/tasks/__init__.py
  - src/gamification/prizes/models.py
  - src/tasks/submissions/router.py
  - src/gamification/badges/service.py
  - src/tasks/submissions/models.py
  - src/gamification/prizes/router.py
  - src/templates/student/submit_task.html
  - scripts/migrate.py
  - src/core/__init__.py
  - src/gamification/badges/models.py
  - src/core/auth/router.py
  - src/tasks/submissions/service.py
  - src/gamification/badges/triggers.py
tests:
  - tests/test_checkin.py
  - tests/test_database.py
  - tests/test_extensions.py
  - tests/test_points.py
  - tests/test_task_templates.py
  - tests/test_classes.py
  - tests/test_submissions.py
  - tests/test_leaderboard.py
  - tests/test_feed.py
  - tests/test_prizes.py
  - tests/test_migration.py
  - tests/test_module_structure.py
  - tests/test_auth.py
  - tests/test_badges.py
  - scripts/migrations/test_example_migration.py
-->

---
### Requirement: Teacher assigns template to a date

Teachers SHALL assign task templates to dates using the schedule rule system (`TaskScheduleRule`) rather than single-date assignment. The assignment UI SHALL present four scheduling modes: once, range (every day), range with weekday filter, and open-ended. All modes SHALL create `TaskAssignment` records through the `expand_schedule_rule()` service function. The previous single-date `AssignTemplateRequest` API endpoint SHALL continue to function for backward compatibility.

#### Scenario: Teacher assigns template using range mode with weekday filter

- **WHEN** a teacher selects "日期區間 + 星期篩選" mode, sets start/end dates, checks weekdays [0,1,3,4], and submits
- **THEN** `POST /classes/{class_id}/schedule-rules` is called with the rule parameters
- **AND** `TaskAssignment` records are created for all qualifying dates in the range
- **AND** the teacher is redirected to the templates list with a success message

#### Scenario: Template assign page shows four scheduling modes

- **WHEN** a teacher opens the schedule assignment page for a template
- **THEN** the page displays a mode selector with options: 一次性、日期區間、星期篩選、開放式
- **AND** the relevant date/weekday inputs update based on the selected mode

#### Scenario: No template assigned for today

- **WHEN** no template is assigned for the current date
- **THEN** students SHALL see a message indicating no task is available today


<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
code:
  - src/gamification/__init__.py
  - src/core/classes/router.py
  - src/core/classes/service.py
  - scripts/__init__.py
  - src/extensions/protocols/reward.py
  - src/extensions/registry/__init__.py
  - src/extensions/protocols/__init__.py
  - src/tasks/checkin/router.py
  - src/templates/teacher/templates_list.html
  - LICENSE
  - uv.lock
  - src/core/users/__init__.py
  - src/gamification/points/service.py
  - src/templates/community/leaderboard.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_form.html
  - src/core/auth/__init__.py
  - src/tasks/templates/models.py
  - src/templates/teacher/points_manage.html
  - src/templates/community/feed.html
  - src/community/feed/router.py
  - src/extensions/protocols/validator.py
  - src/shared/database.py
  - src/core/classes/__init__.py
  - src/tasks/checkin/service.py
  - src/tasks/templates/service.py
  - src/gamification/badges/__init__.py
  - src/gamification/points/models.py
  - src/tasks/checkin/__init__.py
  - src/community/feed/__init__.py
  - src/gamification/prizes/__init__.py
  - src/core/auth/deps.py
  - src/core/auth/jwt.py
  - src/extensions/deps.py
  - docker-compose.yml
  - src/community/__init__.py
  - src/core/auth/local_provider.py
  - src/core/classes/models.py
  - src/gamification/badges/router.py
  - src/gamification/leaderboard/router.py
  - scripts/migrations/__init__.py
  - src/gamification/points/router.py
  - src/main.py
  - src/extensions/registry/core.py
  - src/shared/__init__.py
  - src/tasks/checkin/models.py
  - src/core/users/router.py
  - pytest.ini
  - scripts/migrations/20260317_001_initial_indexes.py
  - src/tasks/submissions/__init__.py
  - src/community/feed/models.py
  - src/core/users/models.py
  - src/gamification/leaderboard/__init__.py
  - src/templates/student/badges.html
  - src/tasks/templates/router.py
  - src/gamification/points/providers.py
  - src/templates/student/dashboard.html
  - src/extensions/protocols/badge.py
  - src/tasks/templates/__init__.py
  - src/core/auth/password.py
  - src/extensions/__init__.py
  - src/gamification/points/__init__.py
  - pyproject.toml
  - src/extensions/protocols/auth.py
  - src/tasks/__init__.py
  - src/gamification/prizes/models.py
  - src/tasks/submissions/router.py
  - src/gamification/badges/service.py
  - src/tasks/submissions/models.py
  - src/gamification/prizes/router.py
  - src/templates/student/submit_task.html
  - scripts/migrate.py
  - src/core/__init__.py
  - src/gamification/badges/models.py
  - src/core/auth/router.py
  - src/tasks/submissions/service.py
  - src/gamification/badges/triggers.py
tests:
  - tests/test_checkin.py
  - tests/test_database.py
  - tests/test_extensions.py
  - tests/test_points.py
  - tests/test_task_templates.py
  - tests/test_classes.py
  - tests/test_submissions.py
  - tests/test_leaderboard.py
  - tests/test_feed.py
  - tests/test_prizes.py
  - tests/test_migration.py
  - tests/test_module_structure.py
  - tests/test_auth.py
  - tests/test_badges.py
  - scripts/migrations/test_example_migration.py
-->

<!-- @trace
source: task-scheduling-and-checkin
updated: 2026-03-19
-->

---
### Requirement: Teacher edits a template

Teachers SHALL be able to edit a template's title, description, and field definitions. Edits SHALL only affect future and unsubmitted assignments; already-submitted entries MUST retain a snapshot of the template version at submission time.

#### Scenario: Template title updated

- **WHEN** a teacher updates the template title
- **THEN** future assignments SHALL use the new title
- **THEN** existing submissions SHALL retain the original title snapshot


<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
code:
  - src/gamification/__init__.py
  - src/core/classes/router.py
  - src/core/classes/service.py
  - scripts/__init__.py
  - src/extensions/protocols/reward.py
  - src/extensions/registry/__init__.py
  - src/extensions/protocols/__init__.py
  - src/tasks/checkin/router.py
  - src/templates/teacher/templates_list.html
  - LICENSE
  - uv.lock
  - src/core/users/__init__.py
  - src/gamification/points/service.py
  - src/templates/community/leaderboard.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_form.html
  - src/core/auth/__init__.py
  - src/tasks/templates/models.py
  - src/templates/teacher/points_manage.html
  - src/templates/community/feed.html
  - src/community/feed/router.py
  - src/extensions/protocols/validator.py
  - src/shared/database.py
  - src/core/classes/__init__.py
  - src/tasks/checkin/service.py
  - src/tasks/templates/service.py
  - src/gamification/badges/__init__.py
  - src/gamification/points/models.py
  - src/tasks/checkin/__init__.py
  - src/community/feed/__init__.py
  - src/gamification/prizes/__init__.py
  - src/core/auth/deps.py
  - src/core/auth/jwt.py
  - src/extensions/deps.py
  - docker-compose.yml
  - src/community/__init__.py
  - src/core/auth/local_provider.py
  - src/core/classes/models.py
  - src/gamification/badges/router.py
  - src/gamification/leaderboard/router.py
  - scripts/migrations/__init__.py
  - src/gamification/points/router.py
  - src/main.py
  - src/extensions/registry/core.py
  - src/shared/__init__.py
  - src/tasks/checkin/models.py
  - src/core/users/router.py
  - pytest.ini
  - scripts/migrations/20260317_001_initial_indexes.py
  - src/tasks/submissions/__init__.py
  - src/community/feed/models.py
  - src/core/users/models.py
  - src/gamification/leaderboard/__init__.py
  - src/templates/student/badges.html
  - src/tasks/templates/router.py
  - src/gamification/points/providers.py
  - src/templates/student/dashboard.html
  - src/extensions/protocols/badge.py
  - src/tasks/templates/__init__.py
  - src/core/auth/password.py
  - src/extensions/__init__.py
  - src/gamification/points/__init__.py
  - pyproject.toml
  - src/extensions/protocols/auth.py
  - src/tasks/__init__.py
  - src/gamification/prizes/models.py
  - src/tasks/submissions/router.py
  - src/gamification/badges/service.py
  - src/tasks/submissions/models.py
  - src/gamification/prizes/router.py
  - src/templates/student/submit_task.html
  - scripts/migrate.py
  - src/core/__init__.py
  - src/gamification/badges/models.py
  - src/core/auth/router.py
  - src/tasks/submissions/service.py
  - src/gamification/badges/triggers.py
tests:
  - tests/test_checkin.py
  - tests/test_database.py
  - tests/test_extensions.py
  - tests/test_points.py
  - tests/test_task_templates.py
  - tests/test_classes.py
  - tests/test_submissions.py
  - tests/test_leaderboard.py
  - tests/test_feed.py
  - tests/test_prizes.py
  - tests/test_migration.py
  - tests/test_module_structure.py
  - tests/test_auth.py
  - tests/test_badges.py
  - scripts/migrations/test_example_migration.py
-->

---
### Requirement: Supported field types

The system SHALL support exactly four field types: `text` (single-line plain text), `markdown` (multi-line with WYSIWYG editor), `number` (integer or decimal), `checkbox` (boolean).

#### Scenario: Markdown field rendered in WYSIWYG editor

- **WHEN** a student opens a task submission form with a markdown-type field
- **THEN** the field SHALL render as an EasyMDE editor with live preview

#### Scenario: Number field rejects non-numeric input

- **WHEN** a student enters non-numeric text in a number-type field
- **THEN** the system SHALL display a validation error and SHALL NOT allow submission


<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
code:
  - src/gamification/__init__.py
  - src/core/classes/router.py
  - src/core/classes/service.py
  - scripts/__init__.py
  - src/extensions/protocols/reward.py
  - src/extensions/registry/__init__.py
  - src/extensions/protocols/__init__.py
  - src/tasks/checkin/router.py
  - src/templates/teacher/templates_list.html
  - LICENSE
  - uv.lock
  - src/core/users/__init__.py
  - src/gamification/points/service.py
  - src/templates/community/leaderboard.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_form.html
  - src/core/auth/__init__.py
  - src/tasks/templates/models.py
  - src/templates/teacher/points_manage.html
  - src/templates/community/feed.html
  - src/community/feed/router.py
  - src/extensions/protocols/validator.py
  - src/shared/database.py
  - src/core/classes/__init__.py
  - src/tasks/checkin/service.py
  - src/tasks/templates/service.py
  - src/gamification/badges/__init__.py
  - src/gamification/points/models.py
  - src/tasks/checkin/__init__.py
  - src/community/feed/__init__.py
  - src/gamification/prizes/__init__.py
  - src/core/auth/deps.py
  - src/core/auth/jwt.py
  - src/extensions/deps.py
  - docker-compose.yml
  - src/community/__init__.py
  - src/core/auth/local_provider.py
  - src/core/classes/models.py
  - src/gamification/badges/router.py
  - src/gamification/leaderboard/router.py
  - scripts/migrations/__init__.py
  - src/gamification/points/router.py
  - src/main.py
  - src/extensions/registry/core.py
  - src/shared/__init__.py
  - src/tasks/checkin/models.py
  - src/core/users/router.py
  - pytest.ini
  - scripts/migrations/20260317_001_initial_indexes.py
  - src/tasks/submissions/__init__.py
  - src/community/feed/models.py
  - src/core/users/models.py
  - src/gamification/leaderboard/__init__.py
  - src/templates/student/badges.html
  - src/tasks/templates/router.py
  - src/gamification/points/providers.py
  - src/templates/student/dashboard.html
  - src/extensions/protocols/badge.py
  - src/tasks/templates/__init__.py
  - src/core/auth/password.py
  - src/extensions/__init__.py
  - src/gamification/points/__init__.py
  - pyproject.toml
  - src/extensions/protocols/auth.py
  - src/tasks/__init__.py
  - src/gamification/prizes/models.py
  - src/tasks/submissions/router.py
  - src/gamification/badges/service.py
  - src/tasks/submissions/models.py
  - src/gamification/prizes/router.py
  - src/templates/student/submit_task.html
  - scripts/migrate.py
  - src/core/__init__.py
  - src/gamification/badges/models.py
  - src/core/auth/router.py
  - src/tasks/submissions/service.py
  - src/gamification/badges/triggers.py
tests:
  - tests/test_checkin.py
  - tests/test_database.py
  - tests/test_extensions.py
  - tests/test_points.py
  - tests/test_task_templates.py
  - tests/test_classes.py
  - tests/test_submissions.py
  - tests/test_leaderboard.py
  - tests/test_feed.py
  - tests/test_prizes.py
  - tests/test_migration.py
  - tests/test_module_structure.py
  - tests/test_auth.py
  - tests/test_badges.py
  - scripts/migrations/test_example_migration.py
-->

---
### Requirement: Teacher deletes a template

Teachers SHALL be able to delete a template. Deletion SHALL be prevented if the template has any submissions already associated with it.

#### Scenario: Template with submissions cannot be deleted

- **WHEN** a teacher attempts to delete a template that has one or more submissions
- **THEN** the system SHALL return an error and SHALL NOT delete the template

<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
code:
  - src/gamification/__init__.py
  - src/core/classes/router.py
  - src/core/classes/service.py
  - scripts/__init__.py
  - src/extensions/protocols/reward.py
  - src/extensions/registry/__init__.py
  - src/extensions/protocols/__init__.py
  - src/tasks/checkin/router.py
  - src/templates/teacher/templates_list.html
  - LICENSE
  - uv.lock
  - src/core/users/__init__.py
  - src/gamification/points/service.py
  - src/templates/community/leaderboard.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_form.html
  - src/core/auth/__init__.py
  - src/tasks/templates/models.py
  - src/templates/teacher/points_manage.html
  - src/templates/community/feed.html
  - src/community/feed/router.py
  - src/extensions/protocols/validator.py
  - src/shared/database.py
  - src/core/classes/__init__.py
  - src/tasks/checkin/service.py
  - src/tasks/templates/service.py
  - src/gamification/badges/__init__.py
  - src/gamification/points/models.py
  - src/tasks/checkin/__init__.py
  - src/community/feed/__init__.py
  - src/gamification/prizes/__init__.py
  - src/core/auth/deps.py
  - src/core/auth/jwt.py
  - src/extensions/deps.py
  - docker-compose.yml
  - src/community/__init__.py
  - src/core/auth/local_provider.py
  - src/core/classes/models.py
  - src/gamification/badges/router.py
  - src/gamification/leaderboard/router.py
  - scripts/migrations/__init__.py
  - src/gamification/points/router.py
  - src/main.py
  - src/extensions/registry/core.py
  - src/shared/__init__.py
  - src/tasks/checkin/models.py
  - src/core/users/router.py
  - pytest.ini
  - scripts/migrations/20260317_001_initial_indexes.py
  - src/tasks/submissions/__init__.py
  - src/community/feed/models.py
  - src/core/users/models.py
  - src/gamification/leaderboard/__init__.py
  - src/templates/student/badges.html
  - src/tasks/templates/router.py
  - src/gamification/points/providers.py
  - src/templates/student/dashboard.html
  - src/extensions/protocols/badge.py
  - src/tasks/templates/__init__.py
  - src/core/auth/password.py
  - src/extensions/__init__.py
  - src/gamification/points/__init__.py
  - pyproject.toml
  - src/extensions/protocols/auth.py
  - src/tasks/__init__.py
  - src/gamification/prizes/models.py
  - src/tasks/submissions/router.py
  - src/gamification/badges/service.py
  - src/tasks/submissions/models.py
  - src/gamification/prizes/router.py
  - src/templates/student/submit_task.html
  - scripts/migrate.py
  - src/core/__init__.py
  - src/gamification/badges/models.py
  - src/core/auth/router.py
  - src/tasks/submissions/service.py
  - src/gamification/badges/triggers.py
tests:
  - tests/test_checkin.py
  - tests/test_database.py
  - tests/test_extensions.py
  - tests/test_points.py
  - tests/test_task_templates.py
  - tests/test_classes.py
  - tests/test_submissions.py
  - tests/test_leaderboard.py
  - tests/test_feed.py
  - tests/test_prizes.py
  - tests/test_migration.py
  - tests/test_module_structure.py
  - tests/test_auth.py
  - tests/test_badges.py
  - scripts/migrations/test_example_migration.py
-->

---
### Requirement: Teacher template list HTML page

The system SHALL serve a task template management page at `GET /pages/teacher/classes/{class_id}/templates`. The page SHALL require `MANAGE_TASKS` permission. It SHALL display all templates for the class and provide links to create new templates.

#### Scenario: Teacher views template list

- **WHEN** a user with `MANAGE_TASKS` permission navigates to `GET /pages/teacher/classes/{class_id}/templates`
- **THEN** the system SHALL display all existing task templates for that class

#### Scenario: Unauthorized user rejected

- **WHEN** a user without `MANAGE_TASKS` permission accesses the templates list page
- **THEN** the system SHALL return HTTP 403

<!-- @trace
source: ui-pages-fastapi-webpage
updated: 2026-03-18
-->


<!-- @trace
source: ui-pages-fastapi-webpage
updated: 2026-03-18
code:
  - src/gamification/points/router.py
  - src/gamification/leaderboard/router.py
  - src/templates/student/dashboard.html
  - src/templates/login.html
  - src/core/auth/permissions.py
  - src/main.py
  - src/pages/deps.py
  - src/gamification/badges/router.py
  - src/templates/shared/base.html
  - src/tasks/templates/router.py
  - src/shared/webpage.py
  - src/tasks/checkin/router.py
  - src/tasks/submissions/router.py
  - src/core/auth/router.py
  - src/core/system/router.py
  - src/pages/__init__.py
  - src/templates/student/submit_task.html
  - src/pages/router.py
  - src/community/feed/router.py
tests:
  - tests/test_pages.py
-->

---
### Requirement: Teacher template form HTML page

The system SHALL serve a task template creation form at `GET /pages/teacher/classes/{class_id}/templates/new`. The page SHALL require `MANAGE_TASKS` permission. If an `error` query parameter is present, the page SHALL display it.

#### Scenario: Teacher views new template form

- **WHEN** a user with `MANAGE_TASKS` permission navigates to `GET /pages/teacher/classes/{class_id}/templates/new`
- **THEN** the system SHALL display an HTML form for creating a new task template

#### Scenario: Error shown after failed creation

- **WHEN** `GET /pages/teacher/classes/{class_id}/templates/new?error=<message>` is requested
- **THEN** the page SHALL display the error message

<!-- @trace
source: ui-pages-fastapi-webpage
updated: 2026-03-18
-->

<!-- @trace
source: ui-pages-fastapi-webpage
updated: 2026-03-18
code:
  - src/gamification/points/router.py
  - src/gamification/leaderboard/router.py
  - src/templates/student/dashboard.html
  - src/templates/login.html
  - src/core/auth/permissions.py
  - src/main.py
  - src/pages/deps.py
  - src/gamification/badges/router.py
  - src/templates/shared/base.html
  - src/tasks/templates/router.py
  - src/shared/webpage.py
  - src/tasks/checkin/router.py
  - src/tasks/submissions/router.py
  - src/core/auth/router.py
  - src/core/system/router.py
  - src/pages/__init__.py
  - src/templates/student/submit_task.html
  - src/pages/router.py
  - src/community/feed/router.py
tests:
  - tests/test_pages.py
-->

---
### Requirement: Teacher can archive a task template

A teacher SHALL be able to archive a task template they manage. Archiving SHALL set `is_archived = True` on the template. An archived template SHALL remain visible in the teacher's template management list (styled differently to indicate archived status). An archived template SHALL NOT be used to fulfill `get_template_for_date()` queries — it behaves as if no template is assigned.

#### Scenario: Teacher archives a template

- **WHEN** a teacher clicks "封存" on a template in the templates list
- **THEN** `PATCH /templates/{template_id}/archive` is called
- **AND** the template's `is_archived` field is set to `True`
- **AND** the template remains visible to the teacher with an "已封存" label

#### Scenario: Archived template hidden from students

- **WHEN** a student visits the submission page on a date assigned to an archived template
- **THEN** the system behaves as if no template is assigned for that date
- **AND** the student cannot submit a task

<!-- @trace
source: ui-polish-and-fixes
updated: 2026-03-19
-->

---
### Requirement: Teacher can unarchive a task template

A teacher SHALL be able to restore an archived template to active status via an "取消封存" action. After unarchiving, the template SHALL once again fulfill `get_template_for_date()` queries normally.

#### Scenario: Teacher unarchives a template

- **WHEN** a teacher clicks "取消封存" on an archived template
- **THEN** `PATCH /templates/{template_id}/unarchive` is called
- **AND** the template's `is_archived` field is set to `False`
- **AND** the template is treated as active again

<!-- @trace
source: ui-polish-and-fixes
updated: 2026-03-19
-->

---
### Requirement: Template modification requires class management permission

The system SHALL verify that the requesting user can manage the class a template belongs to before allowing update, delete, archive, or unarchive operations. The system SHALL load the template, retrieve its `class_id`, load the corresponding Class document, and call `can_manage_class(user, cls)`. If the user cannot manage the class, the system SHALL return HTTP 403.

#### Scenario: Teacher modifies template in own class

- **WHEN** a teacher with `MANAGE_TASKS` permission and teacher membership in class C calls `PATCH /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL proceed with the update normally

#### Scenario: Teacher modifies template in another class

- **WHEN** a teacher with `MANAGE_TASKS` permission but no membership in class C calls `PATCH /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL return HTTP 403

#### Scenario: Class manager modifies any template

- **WHEN** a user with `MANAGE_ALL_CLASSES` permission calls `PATCH /templates/{template_id}` for any template
- **THEN** the system SHALL proceed with the update normally

#### Scenario: Teacher deletes template in another class

- **WHEN** a teacher with `MANAGE_TASKS` permission but no membership in class C calls `DELETE /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL return HTTP 403

<!-- @trace
source: fix-cross-class-access-control
updated: 2026-03-24
-->

---
### Requirement: Task assignment form includes Discord sync option

The task assignment form SHALL include a checkbox "同步到 Discord" that is visible only when the class has a configured Webhook URL.

#### Scenario: Sync checkbox shown when webhook is configured

- **WHEN** a teacher opens the task assignment form for a class with a Webhook URL
- **THEN** the "同步到 Discord" checkbox SHALL be visible

#### Scenario: Sync checkbox hidden when no webhook

- **WHEN** a teacher opens the task assignment form for a class without a Webhook URL
- **THEN** the "同步到 Discord" checkbox SHALL NOT be displayed

<!-- @trace
source: discord-integration
updated: 2026-03-21
-->

<!-- @trace
source: discord-integration
updated: 2026-03-21
code:
  - src/integrations/discord/service.py
  - src/tasks/templates/router.py
  - src/core/classes/router.py
  - src/templates/teacher/class_hub.html
  - src/integrations/__init__.py
  - src/templates/teacher/template_assign.html
  - src/core/classes/models.py
  - src/pages/router.py
  - src/integrations/discord/__init__.py
tests:
  - tests/test_discord_integration.py
-->

---
### Requirement: Teacher template pages enforce class management

The teacher template pages SHALL enforce class-management authorization on the class derived from the URL. Class-scoped pages (`templates_list_page`, `template_form_page` under `/pages/teacher/classes/{class_id}/templates...`) SHALL require `can_manage_class()` on `class_id`; template-scoped pages (`template_edit_page`, `template_assign_page` under `/pages/teacher/templates/{template_id}/...`) SHALL resolve the template's class and require `can_manage_class()` on it. A teacher who does not manage the class SHALL receive HTTP 403 before any template definition, invite code, or Discord-webhook metadata is disclosed.

#### Scenario: Non-managing teacher lists another class's templates

- **WHEN** a teacher who does not manage the class requests its templates list page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose template definitions

#### Scenario: Non-managing teacher opens a template edit or assign page

- **WHEN** a teacher requests the edit or assign page for a template whose class they do not manage
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose the template or its class's Discord-webhook presence

#### Scenario: Managing teacher opens their own template pages

- **WHEN** a teacher who manages the class requests any of these pages
- **THEN** the system SHALL render the page normally
