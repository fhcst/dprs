# migration-scripts Specification

## Purpose

TBD - created by archiving change 'daily-training-submission-system'. Update Purpose after archive.

## Requirements

### Requirement: Migration script structure

Each database migration SHALL be a standalone Python file under `scripts/migrations/` named with format `YYYYMMDD_NNN_description.py`. Each migration file MUST implement `async def forward() -> None` and `async def backward() -> None`.

#### Scenario: Migration file structure valid

- **WHEN** the migration CLI loads a migration file
- **THEN** the file SHALL be importable and SHALL expose both `forward` and `backward` coroutines


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
### Requirement: Migration tracking collection

The system SHALL maintain a `migrations` collection in MongoDB recording which migrations have been applied. Each document MUST store: migration filename, applied timestamp, and direction (forward/backward).

#### Scenario: Applied migration recorded

- **WHEN** a migration's `forward()` runs successfully
- **THEN** the system SHALL insert a record into the `migrations` collection with the filename and timestamp


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
### Requirement: Migration CLI

The system SHALL provide `scripts/migrate.py` as a CLI entry point. It MUST support: `init` (create tracking collection), `up` (apply all pending migrations in order), `down` (roll back the last applied migration), and `status` (list applied and pending migrations). The CLI MUST add the project root directory to `sys.path` at startup to ensure `scripts.migrations.*` modules are importable regardless of the working directory.

#### Scenario: `migrate.py up` applies pending migrations

- **WHEN** `migrate.py up` is invoked and there are pending migration files not in the tracking collection
- **THEN** the CLI SHALL run each pending migration's `forward()` in filename order and record each one

#### Scenario: `migrate.py down` rolls back last migration

- **WHEN** `migrate.py down` is invoked
- **THEN** the CLI SHALL run the most recently applied migration's `backward()` and remove its tracking record

#### Scenario: `migrate.py status` shows state

- **WHEN** `migrate.py status` is invoked
- **THEN** the CLI SHALL print a list of all migration files with their applied/pending status


<!-- @trace
source: docker-entrypoint-auto-migration
updated: 2026-04-04
code:
  - scripts/migrate.py
  - .env.example
  - scripts/docker-entrypoint.sh
  - src/core/users/models.py
  - Dockerfile
-->

---
### Requirement: Migration idempotency check

The CLI SHALL refuse to apply a migration that is already recorded in the tracking collection. Running `up` when all migrations are applied SHALL succeed without error and print a message.

#### Scenario: Already-applied migration skipped

- **WHEN** `migrate.py up` is invoked and all migrations are already applied
- **THEN** the CLI SHALL print "Nothing to migrate" and exit with code 0

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
### Requirement: Automatic migration on container startup

The Docker entrypoint script (`scripts/docker-entrypoint.sh`) SHALL execute `migrate.py init` followed by `migrate.py up` before starting the FastAPI server. If any migration step fails, the container MUST exit immediately without starting the application.

#### Scenario: Container starts with pending migrations

- **WHEN** the Docker container starts and there are unapplied migration files
- **THEN** the entrypoint SHALL run all pending migrations to completion before launching the FastAPI server

#### Scenario: Container starts with no pending migrations

- **WHEN** the Docker container starts and all migrations are already applied
- **THEN** the entrypoint SHALL print "Nothing to migrate." and proceed to start the FastAPI server without error

#### Scenario: Migration fails during container startup

- **WHEN** the Docker container starts and a migration's `forward()` raises an exception
- **THEN** the entrypoint SHALL exit with a non-zero code and the FastAPI server SHALL NOT start


<!-- @trace
source: docker-entrypoint-auto-migration
updated: 2026-04-04
code:
  - scripts/migrate.py
  - .env.example
  - scripts/docker-entrypoint.sh
  - src/core/users/models.py
  - Dockerfile
-->

---
### Requirement: Migration module importable in container environment

The migration CLI (`scripts/migrate.py`) SHALL ensure that the project root directory is in `sys.path` so that `importlib.import_module("scripts.migrations.<name>")` resolves correctly in all execution environments, including Docker containers where the working directory is `/app`.

#### Scenario: Migration loaded inside Docker container

- **WHEN** `migrate.py up` is invoked inside the Docker container at working directory `/app`
- **THEN** the CLI SHALL successfully import each migration file under `scripts/migrations/` without `ModuleNotFoundError`


<!-- @trace
source: docker-entrypoint-auto-migration
updated: 2026-04-04
code:
  - scripts/migrate.py
  - .env.example
  - scripts/docker-entrypoint.sh
  - src/core/users/models.py
  - Dockerfile
-->

---
### Requirement: Scripts directory included in Docker image

The `Dockerfile` SHALL copy the entire `scripts/` directory (including `migrate.py` and `migrations/`) into the Docker image so that the entrypoint can execute migrations at container startup.

#### Scenario: Docker image contains migration files

- **WHEN** the Docker image is built from the Dockerfile
- **THEN** the image SHALL contain `scripts/migrate.py` and all files under `scripts/migrations/` at the path `/app/scripts/`

<!-- @trace
source: docker-entrypoint-auto-migration
updated: 2026-04-04
code:
  - scripts/migrate.py
  - .env.example
  - scripts/docker-entrypoint.sh
  - src/core/users/models.py
  - Dockerfile
-->

---
### Requirement: Migration directory contains only conforming files

The `scripts/migrations/` directory SHALL contain only migration files matching the `YYYYMMDD_NNN_description.py` naming convention, plus `__init__.py` and test fixtures. Files that do not match the convention and are not `__init__.py` or prefixed with `test_` SHALL be removed to prevent confusion about which migrations are active.

#### Scenario: Legacy non-conforming migration file removed

- **WHEN** a developer lists files in `scripts/migrations/`
- **THEN** every `.py` file other than `__init__.py` and `test_*.py` SHALL match the pattern `YYYYMMDD_NNN_*.py`
- **THEN** `role_to_permissions.py` SHALL NOT exist in the directory

<!-- @trace
source: docker-wasm-build-fix
updated: 2026-04-09
code:
  - src/templates/admin/users_list.html
  - src/templates/teacher/badges_manage.html
  - src/templates/teacher/class_hub.html
  - .agents/skills/spectra-ask
  - src/main.py
  - .agents/skills/spectra-apply
  - .agents/skills/spectra-archive
  - .agents/skills/spectra-discuss
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - src/pages/router.py
  - src/templates/student/badges.html
  - src/templates/teacher/points_manage.html
  - scripts/migrations/role_to_permissions.py
  - src/templates/setup.html
  - src/templates/shared/base.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/login.html
  - src/static/css/input.css
  - src/core/users/router.py
  - .agents/skills/spectra-audit
  - .agents/skills/spectra-debug
  - Dockerfile
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - .agents/skills/spectra-ingest
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - docs/uiux-audit/20260408/00-index.md
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/templates_list.html
  - src/templates/teacher/submission_review.html
  - src/templates/student/learning_history.html
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/community/feed.html
  - .agents/skills/spectra-propose
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - src/templates/community/leaderboard.html
  - src/templates/settings.html
  - src/templates/student/class_history.html
  - src/templates/student/dashboard.html
  - crates/dsl-engine/uv.lock
  - src/templates/shared/macros.html
tests:
  - tests/test_dashboard_and_page_bugs.py
  - tests/test_class_hub_page.py
  - tests/test_admin_users.py
  - tests/auth/test_role_migration.py
-->