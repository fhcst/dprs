## ADDED Requirements

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

### Requirement: Migration module importable in container environment

The migration CLI (`scripts/migrate.py`) SHALL ensure that the project root directory is in `sys.path` so that `importlib.import_module("scripts.migrations.<name>")` resolves correctly in all execution environments, including Docker containers where the working directory is `/app`.

#### Scenario: Migration loaded inside Docker container

- **WHEN** `migrate.py up` is invoked inside the Docker container at working directory `/app`
- **THEN** the CLI SHALL successfully import each migration file under `scripts/migrations/` without `ModuleNotFoundError`

### Requirement: Scripts directory included in Docker image

The `Dockerfile` SHALL copy the entire `scripts/` directory (including `migrate.py` and `migrations/`) into the Docker image so that the entrypoint can execute migrations at container startup.

#### Scenario: Docker image contains migration files

- **WHEN** the Docker image is built from the Dockerfile
- **THEN** the image SHALL contain `scripts/migrate.py` and all files under `scripts/migrations/` at the path `/app/scripts/`

## MODIFIED Requirements

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
