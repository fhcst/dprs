# user-auth Specification

## Purpose

TBD - created by archiving change 'daily-training-submission-system'. Update Purpose after archive.

## Requirements

### Requirement: User registration by teacher

Users with `MANAGE_USERS` permission SHALL be able to create new accounts. Each account MUST include a unique username, hashed password, display name, permissions (as an integer from a Role Preset), and an optional `tags` list. The `role` field is removed.

#### Scenario: User admin creates student account

- **WHEN** a user with `MANAGE_USERS` permission submits a valid username, password, display name, and permissions value
- **THEN** the system SHALL create the account with the given permissions and return the new user ID

#### Scenario: Duplicate username rejected

- **WHEN** a user submits a username that already exists
- **THEN** the system SHALL return an error and SHALL NOT create a duplicate account


<!-- @trace
source: rbac-permission-flags
updated: 2026-03-18
code:
  - docker-compose.yml
  - src/core/auth/guards.py
  - src/tasks/templates/router.py
  - src/tasks/checkin/router.py
  - src/core/system/router.py
  - scripts/migrations/role_to_permissions.py
  - src/gamification/prizes/router.py
  - src/core/system/__init__.py
  - src/core/classes/service.py
  - src/gamification/leaderboard/router.py
  - src/core/system/models.py
  - src/tasks/submissions/router.py
  - pyproject.toml
  - src/core/system/startup.py
  - src/community/feed/router.py
  - src/core/auth/jwt.py
  - src/core/auth/deps.py
  - src/core/auth/router.py
  - src/shared/redis.py
  - src/shared/__init__.py
  - tests/auth/__init__.py
  - src/core/classes/router.py
  - src/templates/setup.html
  - src/gamification/badges/router.py
  - src/core/auth/permissions.py
  - src/main.py
  - src/core/users/router.py
  - src/gamification/points/router.py
  - uv.lock
  - src/core/users/models.py
tests:
  - tests/auth/test_role_migration.py
  - tests/test_redis_shared.py
  - tests/auth/test_deps.py
  - tests/auth/test_permissions.py
  - tests/auth/test_user_model.py
  - tests/test_setup_wizard.py
  - tests/auth/test_guards.py
  - tests/test_classes.py
  - tests/test_setup_startup.py
  - tests/test_system_config.py
  - tests/test_auth.py
  - tests/auth/test_user_router.py
-->

---
### Requirement: User model stores permissions as integer and supports tags

The `User` Beanie Document MUST store `permissions: int` instead of `role: str`. The document MUST also include `tags: list[str]` defaulting to an empty list. Both fields MUST be included in all user response schemas.

#### Scenario: User created with permissions preset

- **WHEN** a new user is created with a Role Preset value
- **THEN** the stored `permissions` field MUST equal the integer value of that preset

#### Scenario: User tags are updatable

- **WHEN** a user with `MANAGE_USERS` permission updates another user's tags
- **THEN** the `tags` field MUST be replaced with the new list


<!-- @trace
source: rbac-permission-flags
updated: 2026-03-18
code:
  - docker-compose.yml
  - src/core/auth/guards.py
  - src/tasks/templates/router.py
  - src/tasks/checkin/router.py
  - src/core/system/router.py
  - scripts/migrations/role_to_permissions.py
  - src/gamification/prizes/router.py
  - src/core/system/__init__.py
  - src/core/classes/service.py
  - src/gamification/leaderboard/router.py
  - src/core/system/models.py
  - src/tasks/submissions/router.py
  - pyproject.toml
  - src/core/system/startup.py
  - src/community/feed/router.py
  - src/core/auth/jwt.py
  - src/core/auth/deps.py
  - src/core/auth/router.py
  - src/shared/redis.py
  - src/shared/__init__.py
  - tests/auth/__init__.py
  - src/core/classes/router.py
  - src/templates/setup.html
  - src/gamification/badges/router.py
  - src/core/auth/permissions.py
  - src/main.py
  - src/core/users/router.py
  - src/gamification/points/router.py
  - uv.lock
  - src/core/users/models.py
tests:
  - tests/auth/test_role_migration.py
  - tests/test_redis_shared.py
  - tests/auth/test_deps.py
  - tests/auth/test_permissions.py
  - tests/auth/test_user_model.py
  - tests/test_setup_wizard.py
  - tests/auth/test_guards.py
  - tests/test_classes.py
  - tests/test_setup_startup.py
  - tests/test_system_config.py
  - tests/test_auth.py
  - tests/auth/test_user_router.py
-->

---
### Requirement: Migration maps existing role field to permissions integer

The system SHALL provide a migration script that converts existing `User` documents from `role: "student"` to `permissions = STUDENT` and `role: "teacher"` to `permissions = TEACHER`. The `role` field MUST be removed after migration.

#### Scenario: Student role migrated to permissions

- **WHEN** the migration script runs on a user with `role = "student"`
- **THEN** the user's document MUST have `permissions` set to the `STUDENT` preset integer and `role` field removed

#### Scenario: Teacher role migrated to permissions

- **WHEN** the migration script runs on a user with `role = "teacher"`
- **THEN** the user's document MUST have `permissions` set to the `TEACHER` preset integer and `role` field removed


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
source: rbac-permission-flags
updated: 2026-03-18
code:
  - docker-compose.yml
  - src/core/auth/guards.py
  - src/tasks/templates/router.py
  - src/tasks/checkin/router.py
  - src/core/system/router.py
  - scripts/migrations/role_to_permissions.py
  - src/gamification/prizes/router.py
  - src/core/system/__init__.py
  - src/core/classes/service.py
  - src/gamification/leaderboard/router.py
  - src/core/system/models.py
  - src/tasks/submissions/router.py
  - pyproject.toml
  - src/core/system/startup.py
  - src/community/feed/router.py
  - src/core/auth/jwt.py
  - src/core/auth/deps.py
  - src/core/auth/router.py
  - src/shared/redis.py
  - src/shared/__init__.py
  - tests/auth/__init__.py
  - src/core/classes/router.py
  - src/templates/setup.html
  - src/gamification/badges/router.py
  - src/core/auth/permissions.py
  - src/main.py
  - src/core/users/router.py
  - src/gamification/points/router.py
  - uv.lock
  - src/core/users/models.py
tests:
  - tests/auth/test_role_migration.py
  - tests/test_redis_shared.py
  - tests/auth/test_deps.py
  - tests/auth/test_permissions.py
  - tests/auth/test_user_model.py
  - tests/test_setup_wizard.py
  - tests/auth/test_guards.py
  - tests/test_classes.py
  - tests/test_setup_startup.py
  - tests/test_system_config.py
  - tests/test_auth.py
  - tests/auth/test_user_router.py
-->

---
### Requirement: User login with credentials

The system SHALL authenticate users via username and password. On success, a signed JWT SHALL be issued and stored in an HttpOnly cookie. The API endpoint (`POST /auth/login`) SHALL accept JSON and return JSON. The form endpoint (`POST /pages/login`) SHALL accept form data and redirect.

#### Scenario: Successful API login

- **WHEN** a client submits valid credentials to `POST /auth/login` with JSON body
- **THEN** the system SHALL set an HttpOnly cookie containing a signed JWT and return JSON with permissions

#### Scenario: Successful form login

- **WHEN** a user submits valid credentials via `POST /pages/login` with form data
- **THEN** the system SHALL set an HttpOnly JWT cookie and redirect to `GET /pages/dashboard` (HTTP 302)

#### Scenario: Invalid credentials rejected via API

- **WHEN** a client submits an incorrect password or unknown username to `POST /auth/login`
- **THEN** the system SHALL return HTTP 401 and SHALL NOT set a session cookie

#### Scenario: Invalid credentials rejected via form

- **WHEN** a user submits incorrect credentials via `POST /pages/login`
- **THEN** the system SHALL redirect to `GET /pages/login?error=帳號或密碼錯誤` (HTTP 302) and SHALL NOT set a session cookie


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
### Requirement: JWT-based session management

The system SHALL validate the JWT on every protected request. Tokens MUST include expiry (exp), user ID, and role claims. Expired tokens MUST be rejected.

#### Scenario: Expired token rejected

- **WHEN** a request arrives with an expired JWT cookie
- **THEN** the system SHALL redirect the user to the login page

#### Scenario: Valid token accepted

- **WHEN** a request arrives with a valid, non-expired JWT cookie
- **THEN** the system SHALL allow the request and provide the authenticated user context


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
### Requirement: Role-based access control

The system SHALL enforce role-based access. Pages and endpoints designated for teachers MUST reject requests from students, and vice versa.

#### Scenario: Student accesses teacher-only endpoint

- **WHEN** a student sends a request to a teacher-only endpoint
- **THEN** the system SHALL return a 403 response


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
### Requirement: AuthProvider extension point

The system SHALL define an `AuthProvider` Protocol with method `authenticate(credentials) -> User`. The local (username/password) implementation SHALL be registered by default. Additional providers (e.g., Google OAuth) MUST be registerable without modifying core auth code.

#### Scenario: Default local provider authenticates

- **WHEN** the app starts with no additional providers configured
- **THEN** the LocalAuthProvider SHALL handle all authentication requests

#### Scenario: Additional provider registered

- **WHEN** a new AuthProvider implementation is registered in the ExtensionRegistry at startup
- **THEN** the auth router SHALL delegate to that provider when the corresponding login method is selected


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
### Requirement: Password change

Users SHALL be able to change their own password. The current password MUST be verified before accepting a new one.

#### Scenario: Successful password change

- **WHEN** a user submits their current password and a valid new password
- **THEN** the system SHALL update the stored hash and invalidate existing sessions

#### Scenario: Wrong current password

- **WHEN** a user submits an incorrect current password
- **THEN** the system SHALL return an error and SHALL NOT update the password

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
### Requirement: Browser-based form login endpoint

The system SHALL accept `POST /pages/login` with `application/x-www-form-urlencoded` body containing `username`, `password`, and an optional `next` field. On failure, it SHALL redirect to `GET /pages/login?error=<message>` (HTTP 302) and SHALL NOT set the JWT cookie. On success, it SHALL set the HttpOnly JWT cookie and redirect (HTTP 302) to a post-login destination determined by validating `next` as follows:

- The system SHALL treat a `next` value as a safe redirect target ONLY when it is a single same-origin relative path: it begins with exactly one `/` and does not escape the application origin.
- BEFORE accepting `next`, the system SHALL inspect only the path/authority portion of the value — everything before the first `?` or `#` — and SHALL reject the value when that portion contains a backslash (`\`), begins with `//`, or contains a colon (`:`); the system SHALL also reject any value containing an ASCII control character. The authority checks SHALL deliberately exclude the query/fragment so that a colon or other reserved character appearing only in a query value (for example an ISO timestamp `?ts=2026-06-28T12:00:00`) does not cause a same-origin deep link to be silently dropped. Reaching an empty `urlsplit(next).netloc` alone SHALL NOT be treated as sufficient proof of safety, because an input such as `/\evil.com` yields an empty netloc yet still encodes an off-origin (protocol-relative) redirect once a browser normalizes `\` to `/`.
- When `next` is present and passes validation, the system SHALL redirect to that exact relative path.
- When `next` is absent, empty, or rejected by validation, the system SHALL redirect to `GET /pages/dashboard`.

#### Scenario: Successful form login

- **WHEN** a user submits valid credentials via the HTML login form at `POST /pages/login` with no `next` field
- **THEN** the system SHALL set an HttpOnly JWT cookie and redirect to `GET /pages/dashboard` (HTTP 302)

#### Scenario: Invalid credentials via form

- **WHEN** a user submits invalid credentials via the HTML login form
- **THEN** the system SHALL redirect to `GET /pages/login?error=帳號或密碼錯誤` (HTTP 302)
- **AND** the JWT cookie SHALL NOT be set

#### Scenario: Successful login returns to a safe relative next

- **WHEN** a user submits valid credentials with `next` set to a single same-origin relative path such as `/pages/settings`
- **THEN** the system SHALL redirect (HTTP 302) to that exact relative path `/pages/settings`

#### Scenario: Open-redirect vectors fall back to dashboard

- **WHEN** a user submits valid credentials with `next` set to any of `//evil.com`, `/\evil.com`, `http://evil.com`, or `https://evil.com`
- **THEN** the system SHALL ignore the `next` value and redirect (HTTP 302) to `GET /pages/dashboard`
- **AND** the response `Location` header SHALL NOT contain `evil.com`

#### Scenario: Colon in the query string round-trips

- **WHEN** a user submits valid credentials with `next` set to a same-origin relative path whose query carries a colon, such as `/pages/dashboard?ts=2026-06-28T12:00:00`
- **THEN** the system SHALL accept `next` and redirect (HTTP 302) to that exact relative path including its query string
- **AND** the colon in the query SHALL NOT cause a fallback to `GET /pages/dashboard`

##### Example: next validation outcomes

| next input                              | Validation result | Redirect destination                    |
| --------------------------------------- | ----------------- | --------------------------------------- |
| `/pages/settings`                       | accepted          | `/pages/settings`                       |
| `/pages/dashboard`                      | accepted          | `/pages/dashboard`                      |
| `/pages/dashboard?ts=2026-06-28T12:00:00` | accepted        | `/pages/dashboard?ts=2026-06-28T12:00:00` |
| `//evil.com`                            | rejected          | `/pages/dashboard`                      |
| `/\evil.com`                            | rejected          | `/pages/dashboard`                      |
| `http://evil.com`                       | rejected          | `/pages/dashboard`                      |
| `https://evil.com`                      | rejected          | `/pages/dashboard`                      |


<!-- @trace
source: fix-login-next-redirect
updated: 2026-06-29
code:
  - src/pages/router.py
  - src/pages/deps.py
tests:
  - tests/test_pages.py
-->

---
### Requirement: Email is required when creating a new user account

The system SHALL require a valid email address when creating a new user account.

#### Scenario: User creation fails without email

- **WHEN** an admin submits the create user form without an email address
- **THEN** the system SHALL return a validation error and SHALL NOT create the account

#### Scenario: User creation succeeds with email

- **WHEN** an admin submits the create user form with a valid email address
- **THEN** the system SHALL create the account with the provided email

<!-- @trace
source: user-profile-gravatar
updated: 2026-03-20
-->


<!-- @trace
source: user-profile-gravatar
updated: 2026-03-20
code:
  - src/shared/webpage.py
  - src/shared/gravatar.py
  - src/pages/router.py
  - src/templates/admin/user_form.html
  - src/templates/shared/base.html
  - src/templates/settings.html
tests:
  - tests/test_settings.py
  - tests/test_gravatar_filter.py
-->

---
### Requirement: Browser-based logout redirects to login

The system SHALL accept `POST /auth/logout` and redirect to `GET /pages/login` after clearing the session cookie.

#### Scenario: Successful logout

- **WHEN** a user submits the logout form via `POST /auth/logout`
- **THEN** the system SHALL clear the JWT cookie and redirect to `GET /pages/login` (HTTP 302)

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
### Requirement: Auth cookies use Secure flag in production

The system SHALL set `secure=True` on the `access_token` cookie when `FASTAPI_APP_ENVIRONMENT` is set to `production`. This applies to both the API login endpoint (`POST /auth/login`) and the form login endpoint (`POST /pages/login`). In non-production environments, the `secure` flag MAY be omitted to allow HTTP-based local development.

#### Scenario: Production login sets Secure cookie

- **WHEN** a user successfully authenticates via `POST /auth/login` or `POST /pages/login` in a production environment
- **THEN** the `access_token` cookie SHALL include the `Secure` attribute

#### Scenario: Non-production login omits Secure flag

- **WHEN** a user successfully authenticates in a non-production environment
- **THEN** the `access_token` cookie MAY omit the `Secure` attribute


<!-- @trace
source: security-hardening
updated: 2026-03-25
code:
  - src/shared/sessions.py
  - src/shared/limiter.py
  - docker-compose.yml
  - uv.lock
  - src/core/system/router.py
  - src/core/auth/router.py
  - src/shared/csrf.py
  - pyproject.toml
  - src/core/auth/jwt.py
  - src/main.py
  - src/pages/router.py
tests:
  - tests/test_csrf.py
  - tests/test_setup_startup.py
  - tests/test_identity_tags.py
  - tests/test_security_audit.py
  - tests/test_rate_limiting.py
  - tests/test_secure_cookie.py
  - tests/test_sessions.py
-->

---
### Requirement: Rate limiting on authentication endpoints

The system SHALL enforce rate limiting on authentication-related endpoints to prevent brute-force attacks. The following endpoints SHALL be rate-limited:
- `POST /auth/login`
- `POST /pages/login`
- `POST /auth/change-password`
- `POST /setup`

When the rate limit is exceeded, the system SHALL return HTTP 429 (Too Many Requests).

#### Scenario: Login rate limit exceeded

- **WHEN** a client exceeds the rate limit on `POST /auth/login` or `POST /pages/login`
- **THEN** the system SHALL return HTTP 429 and SHALL NOT attempt authentication

#### Scenario: Requests within rate limit proceed normally

- **WHEN** a client submits login requests within the allowed rate
- **THEN** the system SHALL process authentication normally


<!-- @trace
source: security-hardening
updated: 2026-03-25
code:
  - src/shared/sessions.py
  - src/shared/limiter.py
  - docker-compose.yml
  - uv.lock
  - src/core/system/router.py
  - src/core/auth/router.py
  - src/shared/csrf.py
  - pyproject.toml
  - src/core/auth/jwt.py
  - src/main.py
  - src/pages/router.py
tests:
  - tests/test_csrf.py
  - tests/test_setup_startup.py
  - tests/test_identity_tags.py
  - tests/test_security_audit.py
  - tests/test_rate_limiting.py
  - tests/test_secure_cookie.py
  - tests/test_sessions.py
-->

---
### Requirement: CSRF protection on form POST endpoints

The system SHALL validate the `Origin` or `Referer` header on form-based POST requests to prevent cross-site request forgery. If the header is present and does not match the application's expected origin, the system SHALL reject the request with HTTP 403.

#### Scenario: Form POST with matching Origin accepted

- **WHEN** a form POST request includes an `Origin` header matching the application host
- **THEN** the system SHALL process the request normally

#### Scenario: Form POST with mismatched Origin rejected

- **WHEN** a form POST request includes an `Origin` header that does not match the application host
- **THEN** the system SHALL return HTTP 403 and SHALL NOT process the form submission

---
### Requirement: Password hashing uses Argon2id

The system SHALL hash all passwords using the Argon2id algorithm via the argon2-cffi library. The system SHALL use the library's default parameters, which conform to OWASP recommendations. The system SHALL NOT use bcrypt, passlib, or any other password hashing library.

#### Scenario: New password is hashed with Argon2id

- **WHEN** a user account is created or a password is changed
- **THEN** the stored `hashed_password` SHALL be an Argon2id hash (prefixed with `$argon2id$`)

#### Scenario: Password verification uses Argon2id

- **WHEN** a user attempts to log in with a valid password
- **THEN** the system SHALL verify the password against the Argon2id hash and grant access

#### Scenario: Timing-safe dummy verification for unknown users

- **WHEN** a login attempt is made with a username that does not exist
- **THEN** the system SHALL perform a dummy Argon2id verification to prevent timing side-channel attacks (CWE-208)
- **AND** the dummy hash SHALL be in Argon2id format to ensure consistent timing with real verifications

---
### Requirement: Login redirect preserves the requested page as a relative next

When the page-auth dependency redirects an unauthenticated or unauthorized browser request to the login page, the system SHALL set the `next` query parameter to the originally requested RELATIVE target — the request path, plus the original query string when one is present — and SHALL NOT use the absolute request URL (no scheme, no host). This guarantees the stored `next` matches the single same-origin relative-path format enforced by the login endpoint's `next` validator, so a deep-linked page round-trips back to the user after a successful login.

The system SHALL capture `next` ONLY for idempotent (GET) requests. Because the post-login redirect always replays `next` as a GET, a non-GET protected request (for example an unauthenticated or expired-session `POST /pages/settings/password`) SHALL omit `next` entirely, so login falls back to `GET /pages/dashboard` rather than replaying a GET against a POST-only route and surfacing `405 Method Not Allowed`.

#### Scenario: Unauthenticated deep link stores a relative next

- **WHEN** an unauthenticated browser requests a protected page such as `GET /pages/settings`
- **THEN** the system SHALL redirect (HTTP 302) to the login page with `next` equal to the relative path `/pages/settings`
- **AND** the `next` value SHALL NOT be an absolute `http://` or `https://` URL

#### Scenario: Requested query string is preserved in next

- **WHEN** an unauthenticated browser requests a protected page that carries a query string, such as `GET /pages/dashboard?create_class=1`
- **THEN** the stored `next` SHALL include both the path and the original query string, i.e. `/pages/dashboard?create_class=1`

#### Scenario: Deep link round-trips after login

- **WHEN** a user is redirected to login from a protected page and then submits valid credentials together with the preserved relative `next`
- **THEN** the system SHALL redirect (HTTP 302) the user back to the originally requested page rather than to the dashboard

#### Scenario: Non-GET protected request does not capture next

- **WHEN** an unauthenticated or expired-session browser submits a non-GET request to a protected endpoint, such as `POST /pages/settings/password`
- **THEN** the system SHALL redirect (HTTP 302) to the login page WITHOUT a `next` query parameter (the POST-only path SHALL NOT be stored)
- **AND** a subsequent successful login SHALL fall back to `GET /pages/dashboard` instead of replaying a GET against the POST-only route (which would return `405 Method Not Allowed`)

## ADDED Requirements


<!-- @trace
source: security-hardening
updated: 2026-03-25
code:
  - src/shared/sessions.py
  - src/shared/limiter.py
  - docker-compose.yml
  - uv.lock
  - src/core/system/router.py
  - src/core/auth/router.py
  - src/shared/csrf.py
  - pyproject.toml
  - src/core/auth/jwt.py
  - src/main.py
  - src/pages/router.py
tests:
  - tests/test_csrf.py
  - tests/test_setup_startup.py
  - tests/test_identity_tags.py
  - tests/test_security_audit.py
  - tests/test_rate_limiting.py
  - tests/test_secure_cookie.py
  - tests/test_sessions.py
-->


<!-- @trace
source: migrate-to-argon2-cffi
updated: 2026-04-04
code:
  - pyproject.toml
  - uv.lock
  - src/core/auth/local_provider.py
  - src/core/auth/password.py
tests:
  - tests/test_auth.py
-->


<!-- @trace
source: fix-login-next-redirect
updated: 2026-06-29
code:
  - src/pages/router.py
  - src/pages/deps.py
tests:
  - tests/test_pages.py
-->

### Requirement: JWT secret safety check at startup

The system SHALL check whether the `SESSION_SECRET` environment variable is set to the default development value at application startup. If the default value is detected, the system SHALL log a WARNING to alert operators that the secret must be changed before production use.

#### Scenario: Default secret triggers warning log

- **WHEN** the application starts with `SESSION_SECRET` equal to the default development value
- **THEN** the system SHALL emit a WARNING-level log message indicating that the default secret is in use and must be changed in production

#### Scenario: Custom secret produces no warning

- **WHEN** the application starts with a non-default `SESSION_SECRET` value
- **THEN** the system SHALL NOT emit a warning related to the JWT secret

<!-- @trace
source: security-audit-fixes
updated: 2026-03-23
code:
  - src/core/auth/jwt.py
tests:
  - tests/test_security_audit.py
-->

<!-- @trace
source: security-hardening
updated: 2026-03-25
code:
  - src/shared/sessions.py
  - src/shared/limiter.py
  - docker-compose.yml
  - uv.lock
  - src/core/system/router.py
  - src/core/auth/router.py
  - src/shared/csrf.py
  - pyproject.toml
  - src/core/auth/jwt.py
  - src/main.py
  - src/pages/router.py
tests:
  - tests/test_csrf.py
  - tests/test_setup_startup.py
  - tests/test_identity_tags.py
  - tests/test_security_audit.py
  - tests/test_rate_limiting.py
  - tests/test_secure_cookie.py
  - tests/test_sessions.py
-->

### Requirement: Password hashing uses Argon2id

The system SHALL hash all passwords using the Argon2id algorithm via the argon2-cffi library. The system SHALL use the library's default parameters, which conform to OWASP recommendations. The system SHALL NOT use bcrypt, passlib, or any other password hashing library.

#### Scenario: New password is hashed with Argon2id

- **WHEN** a user account is created or a password is changed
- **THEN** the stored `hashed_password` SHALL be an Argon2id hash (prefixed with `$argon2id$`)

#### Scenario: Password verification uses Argon2id

- **WHEN** a user attempts to log in with a valid password
- **THEN** the system SHALL verify the password against the Argon2id hash and grant access

#### Scenario: Timing-safe dummy verification for unknown users

- **WHEN** a login attempt is made with a username that does not exist
- **THEN** the system SHALL perform a dummy Argon2id verification to prevent timing side-channel attacks (CWE-208)
- **AND** the dummy hash SHALL be in Argon2id format to ensure consistent timing with real verifications