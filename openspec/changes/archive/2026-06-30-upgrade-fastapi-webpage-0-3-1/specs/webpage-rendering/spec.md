## ADDED Requirements

### Requirement: SSR rendering library is pinned to a tagged release

The application SHALL depend on the `fastapi-webpage` server-side rendering library through a git source that is pinned to an explicit release tag. The git source in `pyproject.toml` SHALL NOT be a floating reference (a `git` entry with no `tag` or `rev`). The resolved lockfile entry SHALL record version `0.3.1` and a concrete commit. The container build, which installs dependencies via `uv sync --frozen`, SHALL therefore install exactly the locked release rather than an unpinned upstream HEAD.

#### Scenario: Dependency source is tag-pinned

- **WHEN** the `[tool.uv.sources]` entry for `fastapi-webpage` is inspected
- **THEN** it SHALL include `tag = "v0.3.1"`
- **AND** it SHALL NOT be a floating git source without a tag or rev

#### Scenario: Lockfile records the upgraded version

- **WHEN** the `fastapi-webpage` entry in `uv.lock` is inspected
- **THEN** its `version` SHALL be `0.3.1`
- **AND** its git source SHALL reference the commit that the `v0.3.1` tag points to

#### Scenario: Local virtual environment matches the lock

- **WHEN** `uv sync` has run against the updated lockfile
- **THEN** the installed `fastapi_webpage` package in the local `.venv` SHALL report version `0.3.1`

### Requirement: Gravatar Jinja2 filter is registered on the WebPage template environment

The application SHALL register a `gravatar_url` Jinja2 filter on the shared `WebPage` instance's template environment so that templates can render Gravatar avatar URLs. The registration SHALL succeed against `fastapi-webpage` v0.3.1, whose `WebPage` exposes a Jinja2 `Environment` carrying a `filters` mapping. Rendering a template that applies the `gravatar_url` filter SHALL produce a Gravatar URL string.

#### Scenario: Filter registration target exists in v0.3.1

- **WHEN** the shared `WebPage` instance is constructed under v0.3.1
- **THEN** its template environment SHALL expose a writable `filters` mapping on which `gravatar_url` can be registered without error

#### Scenario: Templates resolve the gravatar filter

- **WHEN** a template applies the `gravatar_url` filter to a user email
- **THEN** the rendered output SHALL contain a `https://www.gravatar.com/avatar/...` URL

##### Example: filter output by email presence

| Input email | Rendered URL |
| ----------- | ------------ |
| `user@example.com` | `https://www.gravatar.com/avatar/<md5(user@example.com)>?d=identicon` |
| empty / none | `https://www.gravatar.com/avatar/?d=identicon` |

### Requirement: Redirect handlers accept tuple, RedirectResponse, and bare-string return shapes

The redirect decorator SHALL accept handler return values in all three shapes used by the application: a `(str, int)` tuple of target URL and status code, a raw `RedirectResponse` object, and a bare URL string. For each shape the framework SHALL produce an HTTP redirect to the resolved target. When a handler returns a bare URL string, the framework SHALL redirect to that target using the status code declared on the decorator. Application redirect targets that are same-origin relative paths (no scheme, no netloc) SHALL be preserved unchanged, and targets that are absolute `http`/`https` URLs SHALL remain valid redirects.

#### Scenario: Tuple return produces a redirect

- **WHEN** a redirect handler returns `(target_url, 302)`
- **THEN** the response SHALL be an HTTP 302 redirect to `target_url`

#### Scenario: RedirectResponse return is honored

- **WHEN** a redirect handler returns a `RedirectResponse` object
- **THEN** the response SHALL redirect to that object's location

#### Scenario: Bare URL string return produces a redirect

- **WHEN** a redirect handler returns a bare URL string (for example `"/"` or a `request.url_for(...)` result)
- **THEN** the response SHALL redirect to that target using the status code declared on the decorator (302)

#### Scenario: Same-origin relative target is preserved

- **WHEN** a redirect handler returns a relative path such as `/pages/dashboard`
- **THEN** the redirect location SHALL remain `/pages/dashboard` unchanged

### Requirement: Page rendering and global context injection are preserved across the upgrade

The page decorator SHALL render the named Jinja2 template with the handler-provided context merged with globally injected context. The application SHALL be able to update global template context at runtime through the `WebPage` context-update method. These behaviors SHALL remain unchanged after the upgrade to v0.3.1, requiring no modification to application page handlers or context-update call sites.

#### Scenario: Page handler renders its template

- **WHEN** a handler decorated as a page returns a context dictionary
- **THEN** the framework SHALL render the named template with that context and return an HTML response

##### Example: login page renders with handler context

- **GIVEN** a page handler bound to template `login.html` that returns `{"error": "帳號或密碼錯誤", "next": None}`
- **WHEN** the route is requested
- **THEN** the response SHALL be HTTP 200 with `Content-Type: text/html` and the rendered body SHALL contain the escaped error text `帳號或密碼錯誤`

#### Scenario: Global context update is reflected in rendered pages

- **WHEN** the application updates global context (for example the configured site name)
- **THEN** subsequently rendered pages SHALL include the updated global context value

##### Example: site name appears after context update

- **GIVEN** the application calls the context-update method with `{"site_name": "FHCST"}`
- **WHEN** any page that references the global `site_name` is rendered afterward
- **THEN** the rendered output SHALL contain `FHCST`

### Requirement: Template autoescape remains uniformly enabled

The rendering environment SHALL keep Jinja2 autoescape enabled for all templates regardless of file extension. Raw HTML output SHALL be produced only where a template explicitly applies the `safe` filter to trusted static markup. The upgrade SHALL NOT change the escaping behavior of existing templates, including those that rely on the `safe` filter for static SVG icons and modal markup.

#### Scenario: Untrusted interpolation stays escaped

- **WHEN** a template interpolates a value without the `safe` filter
- **THEN** the rendered output SHALL HTML-escape that value

#### Scenario: Explicit safe filter still emits raw markup

- **WHEN** a template applies the `safe` filter to a trusted static SVG string
- **THEN** the rendered output SHALL contain that SVG markup unescaped, identically to the pre-upgrade behavior
