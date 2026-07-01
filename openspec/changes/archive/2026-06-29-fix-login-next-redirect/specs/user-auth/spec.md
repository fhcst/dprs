## ADDED Requirements

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

## MODIFIED Requirements

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
