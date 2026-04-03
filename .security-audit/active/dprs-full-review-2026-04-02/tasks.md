## Authentication

- [ ] Review `src/core/auth/jwt.py`, `src/core/auth/password.py`, `src/core/auth/local_provider.py`, and `src/core/auth/router.py` for token verification, password storage, brute-force throttling, and authentication failure behavior.
- [ ] Review `src/core/system/router.py`, `src/core/system/startup.py`, and setup/bootstrap paths in `src/main.py` / `src/pages/router.py` for privileged-account creation and insecure default handling.

## Authorization

- [ ] Review `src/core/classes/router.py`, `src/core/classes/service.py`, `src/tasks/submissions/router.py`, `src/tasks/checkin/router.py`, and `src/pages/deps.py` for class-scoped authorization, IDOR, and ownership enforcement.
- [ ] Review `src/core/users/router.py`, `src/core/system/router.py`, `src/pages/router.py`, and `src/shared/page_context.py` for admin-only access, privilege ceilings, and UI/API authorization mismatches.

## Session Management

- [ ] Review `src/shared/sessions.py`, `src/core/auth/jwt.py`, `src/core/auth/deps.py`, `src/core/auth/router.py`, `src/pages/router.py`, and `src/main.py` for cookie security flags, expiration, invalidation, and duplicated session state.
- [ ] Review `src/shared/csrf.py` plus form-login/page POST flows for CSRF assumptions and request-origin enforcement gaps.

## Input Validation

- [ ] Review `src/tasks/templates/router.py`, `src/tasks/submissions/service.py`, `src/tasks/checkin/router.py`, `src/core/classes/router.py`, and `src/core/users/router.py` for schema validation, range checks, enum restrictions, and rejection of unexpected input.
- [ ] Review `src/integrations/discord/service.py`, `src/templates/teacher/`, `src/templates/shared/`, `src/gamification/triggers/`, and `crates/dsl-engine/src/` for template/rendering safety, parser limits, and user-controlled content handling.

## Injection

- [ ] Review Beanie/Mongo data access across `src/core/`, `src/tasks/`, `src/community/feed/`, and `src/gamification/` for user-controlled identifiers reaching queries without scope checks.
- [ ] Review `src/integrations/discord/service.py`, `src/templates/**/*.html`, `src/gamification/triggers/service.py`, and `crates/dsl-engine/src/` for format-string, HTML/JS, markdown, and DSL-evaluation injection risks.

## Data Protection

- [ ] Review `pyproject.toml`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `src/shared/database.py`, and `src/shared/redis.py` for secret handling, insecure defaults, and deployment exposure.
- [ ] Review `src/core/users/models.py`, `src/core/users/router.py`, `src/pages/router.py`, `src/community/feed/`, `src/core/classes/router.py`, and `src/shared/gravatar.py` for PII overexposure and sensitive field leakage.

## Error Handling

- [ ] Review `src/main.py`, `src/core/auth/`, `src/core/classes/`, `src/tasks/`, `src/gamification/triggers/service.py`, and `src/integrations/discord/service.py` for verbose errors, swallowed exceptions, and failure paths that weaken security guarantees.
- [ ] Review optional-component and external-call fallbacks (`dsl_engine`, Discord, Redis, database startup) for inconsistent state or silent security regression.
