## ADDED Requirements

### Requirement: Single source of truth for production environment detection

The system SHALL determine whether it is running in a production deployment through a single shared helper `is_production()` rather than through inline string comparisons scattered across modules. The helper SHALL normalize the `FASTAPI_APP_ENVIRONMENT` environment variable by trimming surrounding whitespace and lower-casing it, and SHALL treat the deployment as production WHEN the normalized value is either `prod` or `production`. All other values — including `dev`, `development`, `staging`, and an unset variable — SHALL be treated as non-production. The helper SHALL read the environment variable at call time (not at module import time) so that tests can override it.

All previously inline production checks — in JWT secret validation, the auth router, the pages router, and the session middleware — SHALL resolve to this single helper, so that every consumer agrees on what counts as production.

#### Scenario: prod and production both detected as production

- **WHEN** `is_production()` is evaluated with `FASTAPI_APP_ENVIRONMENT` set to `prod`, `production`, or `PROD`
- **THEN** the helper SHALL return `True`

#### Scenario: Development and unset are non-production

- **WHEN** `is_production()` is evaluated with `FASTAPI_APP_ENVIRONMENT` set to `dev`, set to `development`, or not set at all
- **THEN** the helper SHALL return `False`

##### Example: environment normalization outcomes

| `FASTAPI_APP_ENVIRONMENT` | `is_production()` |
| ------------------------- | ----------------- |
| `prod`                    | `True`            |
| `production`              | `True`            |
| `PROD`                    | `True`            |
| `  production  `          | `True`            |
| `dev`                     | `False`           |
| `development`             | `False`           |
| `staging`                 | `False`           |
| (unset)                   | `False`           |

## MODIFIED Requirements

### Requirement: JWT secret safety check at startup

The system SHALL validate the session secret actually used to sign JWTs and the session cookie at application startup via `check_secret_safety()`. The session secret SHALL be resolved through a single shared resolver so that JWT signing and the `SessionMiddleware` use the SAME secret; when `SESSION_SECRET` is unset, the resolver SHALL fall back to a process-stable random value (acceptable for development convenience) rather than diverging between consumers.

A secret SHALL be considered INSECURE when ANY of the following hold:

- it contains the default development value (`dev-secret-change-in-production`) as a substring — covering both an exact match and any value formed by padding the default with extra characters (e.g. `dev-secret-change-in-production!!`), so a near-default secret cannot slip through merely by exceeding the length threshold, OR
- it contains the substring `changeme` (case-insensitive), which covers the published `.env.example` value `changeme_session`, OR
- it is 32 characters or shorter (a real `secrets.token_hex(32)` produces 64 hexadecimal characters). The boundary is inclusive so an at-boundary 32-character value — such as the default padded with one extra character — is rejected rather than slipping through.

WHEN the resolved secret is insecure AND `is_production()` is `True`, the system SHALL raise a `RuntimeError` with an actionable message and SHALL NOT complete startup. WHEN the resolved secret is insecure AND the environment is non-production, the system SHALL emit a WARNING-level log message but SHALL NOT prevent startup. The function SHALL remain importable and callable in isolation for testing, and SHALL accept an optional explicit secret argument so the policy can be exercised without mutating environment state.

#### Scenario: Production with default secret refuses to start

- **WHEN** the application starts with `FASTAPI_APP_ENVIRONMENT` normalizing to production and the resolved secret equal to the default development value
- **THEN** the system SHALL raise a `RuntimeError` and SHALL NOT complete startup

#### Scenario: Production with padded-default secret refuses to start

- **WHEN** the application starts in production with `SESSION_SECRET` set to the default development value padded with extra characters (e.g. `dev-secret-change-in-production!!`, longer than 32 characters)
- **THEN** the system SHALL raise a `RuntimeError` because the secret still contains the default development value

#### Scenario: Production with changeme secret refuses to start

- **WHEN** the application starts in production with `SESSION_SECRET` set to `changeme_session`
- **THEN** the system SHALL raise a `RuntimeError` because the secret contains `changeme`

#### Scenario: Production with too-short secret refuses to start

- **WHEN** the application starts in production with a `SESSION_SECRET` of 32 characters or shorter (including an at-boundary value exactly 32 characters long)
- **THEN** the system SHALL raise a `RuntimeError`

#### Scenario: Production with strong secret starts normally

- **WHEN** the application starts in production with a strong 64-hexadecimal-character `SESSION_SECRET`
- **THEN** the system SHALL start normally without raising or warning about the JWT secret

#### Scenario: Non-production with weak secret logs warning

- **WHEN** the application starts in a non-production environment with an insecure secret (default, `changeme`, or shorter than 32 characters)
- **THEN** the system SHALL emit a WARNING-level log message but SHALL NOT raise or prevent startup

### Requirement: Auth cookies use Secure flag in production

The system SHALL set `secure=True` on the `access_token` cookie when the deployment is production as determined by the shared `is_production()` helper — that is, when `FASTAPI_APP_ENVIRONMENT` normalizes to either `prod` or `production`. This applies to both the API login endpoint (`POST /auth/login`) and the form login endpoint (`POST /pages/login`), and to the session cookie issued by `SessionMiddleware`. In non-production environments, the `secure` flag MAY be omitted to allow HTTP-based local development.

#### Scenario: Production login sets Secure cookie

- **WHEN** a user successfully authenticates via `POST /auth/login` or `POST /pages/login` while `is_production()` is `True` (including `FASTAPI_APP_ENVIRONMENT=prod`)
- **THEN** the `access_token` cookie SHALL include the `Secure` attribute

#### Scenario: Non-production login omits Secure flag

- **WHEN** a user successfully authenticates while `is_production()` is `False`
- **THEN** the `access_token` cookie MAY omit the `Secure` attribute
