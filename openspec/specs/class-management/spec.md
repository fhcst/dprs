# class-management Specification

## Purpose

TBD - created by archiving change 'daily-training-submission-system'. Update Purpose after archive.

## Requirements

### Requirement: Teacher creates a class

Teachers SHALL be able to create a class with a name, description, and visibility setting (public or private). The creating teacher SHALL automatically become a class owner and be added as a `teacher` member. A user MUST hold `MANAGE_OWN_CLASS` or `MANAGE_ALL_CLASSES` permission to create a class.

#### Scenario: Successful class creation

- **WHEN** a user with `MANAGE_OWN_CLASS` submits a valid class name and visibility setting
- **THEN** the system SHALL create the class, assign the user as owner, and add a `ClassMembership` with role `teacher` for that user


<!-- @trace
source: permission-identity-refactor
updated: 2026-03-19
code:
  - src/core/classes/router.py
  - src/core/users/schemas.py
  - src/core/classes/service.py
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/teacher/class_members.html
  - src/pages/router.py
  - src/core/auth/router.py
  - src/tasks/checkin/router.py
  - src/tasks/templates/router.py
  - src/core/classes/models.py
  - src/templates/admin/classes_list.html
  - scripts/migrations/20260319_003_init_identity_tags.py
  - src/community/feed/router.py
  - src/core/users/models.py
  - src/gamification/leaderboard/router.py
  - src/templates/admin/layout.html
  - src/templates/admin/user_form.html
  - src/templates/admin/users_list.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_assign.html
  - src/templates/teacher/template_form.html
  - scripts/migrations/20260319_002_manage_class_rename.py
  - src/core/auth/permissions.py
tests:
  - tests/test_class_permissions.py
  - tests/test_admin_permissions.py
  - tests/test_identity_tags.py
  - tests/test_auth.py
  - tests/auth/test_user_model.py
  - tests/test_user_visibility.py
  - tests/auth/test_guards.py
  - tests/auth/test_permissions.py
-->

---
### Requirement: Student joins a class

The system SHALL NOT create duplicate ClassMembership records. Before inserting a new ClassMembership, the service layer SHALL check if a membership already exists for the given (class_id, user_id) pair. If a membership already exists, the insert SHALL be skipped silently. This applies to all membership creation paths: join-request approval, batch invite, and direct join.

#### Scenario: Approval does not duplicate existing membership

- **WHEN** a join request is approved for a student who already has a ClassMembership in that class
- **THEN** the system SHALL NOT insert a second ClassMembership record

#### Scenario: First-time approval creates membership

- **WHEN** a join request is approved for a student who has no existing ClassMembership in that class
- **THEN** the system SHALL insert a new ClassMembership record with role "student"


<!-- @trace
source: fix-codex-review-findings
updated: 2026-04-03
code:
  - .agents/workflows
  - .agents/skills/spectra-discuss
  - .agents/workflows/spectra-ingest.md
  - .github/skills/spectra-ask/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-002.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-004.md
  - .github/prompts/spectra-debug.prompt.md
  - .github/prompts/spectra-propose.prompt.md
  - .github/skills/spectra-archive/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-005.md
  - .security-audit/active/dprs-full-review-2026-04-02/scope.md
  - .agents/skills/spectra-propose/SKILL.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/workflows/spectra-ask.md
  - .github/skills/spectra-audit/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/.audit.yaml
  - .agents/workflows/spectra-archive.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-003.md
  - .agents/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-ingest
  - .agents/workflows/spectra-apply.md
  - .github/skills/spectra-apply/SKILL.md
  - .github/skills/spectra-propose/SKILL.md
  - AGENTS.md
  - .agents/workflows/spectra-propose.md
  - .agents/skills/spectra-archive/SKILL.md
  - .github/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - .agents/skills/spectra-audit
  - .security-audit/active/dprs-full-review-2026-04-02/tasks.md
  - .github/prompts/spectra-archive.prompt.md
  - .agents/skills/spectra-debug
  - GEMINI.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-001.md
  - .agents/skills/spectra-audit/SKILL.md
  - .github/prompts/spectra-apply.prompt.md
  - .github/skills/spectra-ingest/SKILL.md
  - .github/prompts/spectra-ask.prompt.md
  - .github/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply
  - .agents/skills
  - .agents/skills/spectra-propose
  - .github/prompts/spectra-discuss.prompt.md
  - .github/prompts/spectra-ingest.prompt.md
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-archive
  - .agents/skills/spectra-ask
  - .github/prompts/spectra-audit.prompt.md
  - .security-audit/active/dprs-full-review-2026-04-02/plan.md
  - .agents/workflows/spectra-debug.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .codex/environments/environment.toml
  - .agents/workflows/spectra-audit.md
  - .agents/workflows/spectra-discuss.md
-->

---
### Requirement: Class visibility control

Teachers SHALL be able to set a class as public (visible to all students) or private (invite-only). This setting SHALL apply to leaderboard and community feed visibility outside the class.

#### Scenario: Private class not shown in public listing

- **WHEN** a student browses the public class list
- **THEN** private classes SHALL NOT appear in the results


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
### Requirement: Teacher manages class members

A user SHALL be able to manage a class's members only if they hold `MANAGE_ALL_CLASSES`, or if they hold `MANAGE_OWN_CLASS` AND have a `ClassMembership` with role `teacher` in that class. Management operations include: removing students, promoting co-teachers, and regenerating the invite code. The system MUST reject management operations from users who do not satisfy these conditions with HTTP 403. The class members page SHALL use a two-column layout: the left column for batch invite search and the right column for the current member list. The page SHALL NOT display the invite code (moved to class hub page).

#### Scenario: Class teacher manages their own class

- **WHEN** a user with `MANAGE_OWN_CLASS` and a `teacher` membership in class C sends a management request for class C
- **THEN** the request MUST proceed normally

#### Scenario: User with MANAGE_OWN_CLASS cannot manage another teacher's class

- **WHEN** a user with `MANAGE_OWN_CLASS` but no `teacher` membership in class C sends a management request for class C
- **THEN** the system MUST return HTTP 403

#### Scenario: ClassManager manages any class

- **WHEN** a user with `MANAGE_ALL_CLASSES` sends a management request for any class
- **THEN** the request MUST proceed regardless of membership

#### Scenario: Teacher removes a student

- **WHEN** an authorized teacher removes a student from a class
- **THEN** the student SHALL no longer appear in the class roster and SHALL NOT be able to submit tasks for that class

#### Scenario: Members page uses two-column layout

- **WHEN** a teacher views the class members page
- **THEN** the page SHALL display a two-column layout with batch invite search on the left and current member list on the right

#### Scenario: Members page does not show invite code

- **WHEN** a teacher views the class members page
- **THEN** the page SHALL NOT display the class invite code section (invite code is on the class hub page)

---
### Requirement: Class invite code regeneration

Authorized class managers (satisfying `can_manage_class`) SHALL be able to regenerate the invite code. The old code MUST become invalid immediately upon regeneration.

#### Scenario: Invite code regenerated by authorized teacher

- **WHEN** an authorized teacher regenerates the invite code for their class
- **THEN** the new code SHALL be active and the previous code SHALL be rejected for all future join attempts


<!-- @trace
source: permission-identity-refactor
updated: 2026-03-19
code:
  - src/core/classes/router.py
  - src/core/users/schemas.py
  - src/core/classes/service.py
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/teacher/class_members.html
  - src/pages/router.py
  - src/core/auth/router.py
  - src/tasks/checkin/router.py
  - src/tasks/templates/router.py
  - src/core/classes/models.py
  - src/templates/admin/classes_list.html
  - scripts/migrations/20260319_003_init_identity_tags.py
  - src/community/feed/router.py
  - src/core/users/models.py
  - src/gamification/leaderboard/router.py
  - src/templates/admin/layout.html
  - src/templates/admin/user_form.html
  - src/templates/admin/users_list.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_assign.html
  - src/templates/teacher/template_form.html
  - scripts/migrations/20260319_002_manage_class_rename.py
  - src/core/auth/permissions.py
tests:
  - tests/test_class_permissions.py
  - tests/test_admin_permissions.py
  - tests/test_identity_tags.py
  - tests/test_auth.py
  - tests/auth/test_user_model.py
  - tests/test_user_visibility.py
  - tests/auth/test_guards.py
  - tests/auth/test_permissions.py
-->

---
### Requirement: Teacher batch-invites students to a class

A user authorized to manage a class SHALL be able to search for students not yet in that class and directly add multiple students in a single operation. The search MUST support filtering by administrative class name (`student_profile.class_name`) or real name (`name`). Invited students SHALL be added immediately as members with role `student` without requiring student confirmation.

#### Scenario: Teacher searches students by administrative class name

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/search?q=302&type=class_name`
- **THEN** the system SHALL return a list of users with `STUDENT` identity tag whose `student_profile.class_name` contains `"302"` and who are NOT already members of class `{class_id}`

#### Scenario: Teacher searches students by name

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/search?q=陳&type=name`
- **THEN** the system SHALL return a list of users with `STUDENT` identity tag whose `name` contains `"陳"` and who are NOT already members of class `{class_id}`

#### Scenario: Teacher batch-adds students

- **WHEN** an authorized teacher sends `POST /classes/{class_id}/invite/batch` with a list of user IDs
- **THEN** all specified users SHALL be added as members of class `{class_id}` with role `student`, and users already in the class MUST be silently skipped

#### Scenario: Unauthorized user cannot batch-invite

- **WHEN** a user who does not satisfy `can_manage_class` for the given class sends `POST /classes/{class_id}/invite/batch`
- **THEN** the system MUST return HTTP 403

<!-- @trace
source: permission-identity-refactor
updated: 2026-03-19
code:
  - src/core/classes/router.py
  - src/core/users/schemas.py
  - src/core/classes/service.py
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/teacher/class_members.html
  - src/pages/router.py
  - src/core/auth/router.py
  - src/tasks/checkin/router.py
  - src/tasks/templates/router.py
  - src/core/classes/models.py
  - src/templates/admin/classes_list.html
  - scripts/migrations/20260319_003_init_identity_tags.py
  - src/community/feed/router.py
  - src/core/users/models.py
  - src/gamification/leaderboard/router.py
  - src/templates/admin/layout.html
  - src/templates/admin/user_form.html
  - src/templates/admin/users_list.html
  - src/templates/shared/base.html
  - src/templates/teacher/template_assign.html
  - src/templates/teacher/template_form.html
  - scripts/migrations/20260319_002_manage_class_rename.py
  - src/core/auth/permissions.py
tests:
  - tests/test_class_permissions.py
  - tests/test_admin_permissions.py
  - tests/test_identity_tags.py
  - tests/test_auth.py
  - tests/auth/test_user_model.py
  - tests/test_user_visibility.py
  - tests/auth/test_guards.py
  - tests/auth/test_permissions.py
-->
---
### Requirement: Class list view separates active and archived classes

The class management view SHALL visually separate active classes from archived classes using a tab interface.

#### Scenario: Active and archived classes in separate tabs

- **WHEN** the class list is rendered
- **THEN** active (non-archived) classes SHALL appear in the 運作中 tab and archived classes SHALL appear in the 已封存 tab

#### Scenario: Tab counts reflect actual class counts

- **WHEN** the class list is rendered
- **THEN** each tab label SHALL display the count of classes in that category

<!-- @trace
source: teacher-class-ux-refactor
updated: 2026-03-20
-->

<!-- @trace
source: teacher-class-ux-refactor
updated: 2026-03-20
code:
  - src/templates/shared/base.html
  - src/templates/teacher/class_hub.html
  - src/pages/router.py
  - src/templates/admin/classes_list.html
tests:
  - tests/test_bug_fixes.py
  - tests/test_class_hub_page.py
-->

<!-- @trace
source: teacher-class-ux-refactor
updated: 2026-03-21
code:
  - CLAUDE.md
-->

---
### Requirement: Class stores optional Discord Webhook URL

The Class model SHALL include an optional field `discord_webhook_url` (string, nullable) for storing the class Discord integration endpoint.

#### Scenario: New class has null webhook URL

- **WHEN** a new class is created
- **THEN** `discord_webhook_url` SHALL default to null

#### Scenario: Webhook URL is only visible to class managers

- **WHEN** a student views class information
- **THEN** the `discord_webhook_url` SHALL NOT be exposed in any student-facing API response or template

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
### Requirement: Class model includes Discord template embedded field

The Class model SHALL include an optional field `discord_template` (embedded document, nullable, default `None`) with sub-fields `title_format` (string), `description_template` (string), and `footer_text` (string). This field SHALL be stored as an embedded document within the class record, not as a separate collection.

#### Scenario: Existing classes are unaffected

- **WHEN** the system reads a class document that was created before the `discord_template` field existed
- **THEN** the `discord_template` field SHALL resolve to `None` and the system SHALL operate using system default template values

#### Scenario: discord_template field is not exposed to students

- **WHEN** a student views class information
- **THEN** the `discord_template` field SHALL NOT be included in any student-facing API response or template

<!-- @trace
source: dc-template-msg-editor
updated: 2026-03-25
code:
  - src/core/system/models.py
  - src/templates/teacher/template_assign.html
  - src/templates/teacher/class_hub.html
  - src/core/classes/service.py
  - src/integrations/discord/service.py
  - uv.lock
  - src/core/classes/models.py
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - scripts/migrations/20260325_004_join_request_index.py
  - src/core/system/router.py
  - src/tasks/templates/router.py
  - src/shared/page_context.py
  - src/templates/admin/system_settings.html
  - src/main.py
  - src/templates/student/dashboard.html
  - src/core/classes/router.py
tests:
  - tests/test_dc_template.py
  - tests/test_discord_integration.py
  - tests/test_join_requests.py
-->