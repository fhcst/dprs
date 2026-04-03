## Methodology

Static source code review following OWASP Code Review Guide v2 and OWASP WSTG v4.2. The review prioritizes authentication boundaries, class-scoped authorization, session/cookie handling, user-controlled input flows, server-side rendering sinks, DSL parsing/evaluation boundaries, external webhook integrations, and failure paths that could expose internals or bypass security controls.

## Review Categories

### Authentication
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, authentication category
- **Code Patterns**:
  - JWT creation/verification and secret management
  - Password hashing, password-change logic, and brute-force throttling
  - Bootstrap/setup flows that create privileged users
  - Authentication provider registration and fallback behavior

### Authorization
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, authorization category
- **Code Patterns**:
  - Missing `Depends(...)` / permission guards on routes
  - Class-scoped access checks and IDOR on `class_id`, `request_id`, `submission_id`, and similar identifiers
  - Privilege-ceiling enforcement on user and class-management operations
  - Separation between page visibility checks and API-side enforcement

### Session Management
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, session-management category
- **Code Patterns**:
  - Cookie flags (`HttpOnly`, `Secure`, `SameSite`) and lifetime handling
  - Session fixation or failure to invalidate state after login/password change
  - Mixed use of JWT auth cookie and custom session cookie middleware
  - CSRF assumptions across form and JSON request paths

### Input Validation
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, input-validation category
- **Code Patterns**:
  - Missing length/range/format constraints on request models and query parameters
  - Validation gaps on class invite codes, webhook URLs, dates, and review actions
  - Unsafe handling of rich text, template variables, and user-supplied field payloads
  - Parser/resource-exhaustion risks in the Rust DSL engine and Python integration layer

### Injection
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, injection category
- **Code Patterns**:
  - User-controlled values flowing into Mongo/Beanie queries without scope checks
  - Template, HTML, markdown, or format-string injection in Discord/template rendering
  - Unsafe dynamic evaluation or DSL execution paths
  - Client-side sinks such as `innerHTML` fed by server-controlled or user-controlled content

### Data Protection
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, data-protection category
- **Code Patterns**:
  - Secrets/default credentials in source or configuration defaults
  - PII overexposure in API/page responses and community features
  - Sensitive service URLs and webhook values exposed to inappropriate roles
  - Storage and transmission handling for auth tokens, passwords, and class/user metadata

### Error Handling
- **Source**: OWASP Code Review Guide v2 / OWASP WSTG v4.2, error-handling category
- **Code Patterns**:
  - Exceptions that leak internal details to clients
  - Broad `except Exception` blocks that swallow security failures
  - External-call failures (Discord, optional DSL engine) that leave unsafe or inconsistent state
  - Setup/startup failure handling around secret safety, Redis, and database initialization
