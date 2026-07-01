## MODIFIED Requirements

### Requirement: JWT secret safety check at startup

The system SHALL call `check_secret_safety()` during application startup. If the `FASTAPI_APP_ENVIRONMENT` is set to `production` and the `SESSION_SECRET` is still the default development value, the system SHALL raise a `RuntimeError` and refuse to start. In non-production environments, the system SHALL continue to log a WARNING when the default secret is detected.

#### Scenario: Production with default secret refuses to start

- **WHEN** the application starts with `FASTAPI_APP_ENVIRONMENT` set to `production` and `SESSION_SECRET` equal to the default development value
- **THEN** the system SHALL raise a `RuntimeError` and SHALL NOT complete startup

#### Scenario: Production with custom secret starts normally

- **WHEN** the application starts with `FASTAPI_APP_ENVIRONMENT` set to `production` and a non-default `SESSION_SECRET` value
- **THEN** the system SHALL start normally without errors or warnings related to the JWT secret

#### Scenario: Non-production with default secret logs warning

- **WHEN** the application starts in a non-production environment with `SESSION_SECRET` equal to the default development value
- **THEN** the system SHALL emit a WARNING-level log message but SHALL NOT prevent startup

## ADDED Requirements

### Requirement: Auth cookies use Secure flag in production

The system SHALL set `secure=True` on the `access_token` cookie when `FASTAPI_APP_ENVIRONMENT` is set to `production`. This applies to both the API login endpoint (`POST /auth/login`) and the form login endpoint (`POST /pages/login`). In non-production environments, the `secure` flag MAY be omitted to allow HTTP-based local development.

#### Scenario: Production login sets Secure cookie

- **WHEN** a user successfully authenticates via `POST /auth/login` or `POST /pages/login` in a production environment
- **THEN** the `access_token` cookie SHALL include the `Secure` attribute

#### Scenario: Non-production login omits Secure flag

- **WHEN** a user successfully authenticates in a non-production environment
- **THEN** the `access_token` cookie MAY omit the `Secure` attribute

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

### Requirement: CSRF protection on form POST endpoints

The system SHALL validate the `Origin` or `Referer` header on form-based POST requests to prevent cross-site request forgery. If the header is present and does not match the application's expected origin, the system SHALL reject the request with HTTP 403.

#### Scenario: Form POST with matching Origin accepted

- **WHEN** a form POST request includes an `Origin` header matching the application host
- **THEN** the system SHALL process the request normally

#### Scenario: Form POST with mismatched Origin rejected

- **WHEN** a form POST request includes an `Origin` header that does not match the application host
- **THEN** the system SHALL return HTTP 403 and SHALL NOT process the form submission
