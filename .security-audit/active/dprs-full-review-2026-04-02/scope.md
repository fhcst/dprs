## Audit Target

- **Project**: Daily Practice Report System (DPRS)
- **Repository**: /Users/phoenix/dev/edu-projects/daily-training-submit-system
- **Version/Commit**: staging @ c893a316d11a72ebe937e99d58498b915dd62a29

## Boundaries

### Included

- `src/main.py`
- `src/core/auth/`
- `src/core/users/`
- `src/core/classes/`
- `src/core/system/`
- `src/tasks/checkin/`
- `src/tasks/templates/`
- `src/tasks/submissions/`
- `src/gamification/`
- `src/community/feed/`
- `src/pages/`
- `src/shared/`
- `src/extensions/`
- `src/integrations/discord/`
- `crates/dsl-engine/`
- `pyproject.toml`
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `scripts/`

### Excluded

- `tests/` — test code is used as supporting evidence, not as a primary audit target
- `openspec/` — handled in a separate spec/architecture consistency pass, not as part of OWASP source review artifacts
- `docs/` — documentation is reviewed for consistency separately, not for security enforcement
- `.security-audit/` — audit output, not application code
- `uv.lock` and `crates/dsl-engine/Cargo.lock` — dependency lockfiles are not the primary focus of this source review
- `src/templates/` static markup assets are only reviewed when directly relevant to a server-side trust boundary or rendering sink

## Technology Stack

- Python 3.13 + FastAPI + Pydantic
- Beanie ODM + MongoDB
- Redis for setup state and shared runtime state
- SlowAPI for rate limiting
- Jinja2 via `fastapi-webpage` for SSR pages
- Rust `dsl-engine` crate with PyO3 and WASM targets
- Docker / Docker Compose deployment

## Threat Model

- **Threat Actors**: unauthenticated external users, authenticated students, authenticated teachers/class managers, site administrators, and operators deploying the stack with insecure defaults
- **Attack Surfaces**: login/session flows, setup/bootstrap flow, class membership and join-request endpoints, task submission and review endpoints, check-in endpoints, admin pages, Discord webhook configuration, trigger-rule/DSL handling, and server-side rendered pages
- **Trust Boundaries**: browser ↔ FastAPI application, FastAPI ↔ MongoDB, FastAPI ↔ Redis, FastAPI ↔ Discord webhook endpoint, Python application ↔ Rust DSL engine, and application runtime ↔ environment-variable / container configuration

## Applicable Standards

- OWASP Code Review Guide v2
- OWASP Web Security Testing Guide (WSTG) v4.2
- Review categories selected for this stack: Authentication, Authorization, Session Management, Input Validation, Injection, Data Protection, Error Handling

## Constraints

- Static source review only; no live penetration test against a deployed instance
- Findings must be grounded in the current checked-out worktree, which is dirty and contains unrelated deletions under `.agent/skills/`
- OpenSpec alignment is reviewed in parallel, but spec edits are not applied during the OWASP artifact generation phase
- External dependency CVE triage is out of scope unless the application code relies on an insecure usage pattern
