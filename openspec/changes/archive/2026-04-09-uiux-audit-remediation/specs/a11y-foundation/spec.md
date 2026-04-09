## ADDED Requirements

### Requirement: Reduced motion support

The system SHALL include a global CSS rule that respects the `prefers-reduced-motion: reduce` media query. When this preference is active, all CSS transitions and animations SHALL complete in 0.01ms or less. JavaScript-driven animations SHALL also check this preference and skip animation when active.

#### Scenario: User has reduced motion preference enabled

- **WHEN** the user's operating system has `prefers-reduced-motion: reduce` enabled
- **THEN** all CSS `transition-duration` and `animation-duration` values SHALL be overridden to 0.01ms
- **THEN** scroll behavior SHALL be set to `auto` (instant) instead of `smooth`

#### Scenario: User has no motion preference set

- **WHEN** the user's operating system has no `prefers-reduced-motion` preference or it is set to `no-preference`
- **THEN** all existing transitions and animations SHALL function normally

### Requirement: Skip-to-content link

The system SHALL provide a visually hidden skip link as the first focusable element in the DOM. The skip link SHALL become visible when focused and SHALL navigate to the main content area.

#### Scenario: Keyboard user tabs into the page

- **WHEN** a keyboard user presses Tab on page load
- **THEN** the first focused element SHALL be a "Skip to main content" link
- **THEN** the link SHALL become visually visible when focused
- **THEN** activating the link SHALL move focus to the `<main>` content area

#### Scenario: Mouse user loads the page

- **WHEN** a mouse user loads any page
- **THEN** the skip link SHALL NOT be visible in the normal layout

### Requirement: ARIA landmarks for dynamic content

All dynamically inserted status messages (error banners, success banners, toast notifications) SHALL have appropriate ARIA roles. Error/success alert boxes SHALL have `role="alert"`. Dynamically updating status regions (toast container, pending counts) SHALL have `aria-live="polite"`.

#### Scenario: Login error is displayed

- **WHEN** a user submits invalid credentials and the login page reloads with an error message
- **THEN** the error message container SHALL have `role="alert"`

#### Scenario: Toast notification appears

- **WHEN** an async operation completes and a toast notification is shown
- **THEN** the toast container SHALL have `aria-live="polite"` and `role="status"`
- **THEN** the screen reader SHALL announce the toast content

### Requirement: Non-color status indicators

All status indicators that currently rely on color alone SHALL include an additional non-color differentiator (icon, text label, or pattern). Specifically: point transaction amounts SHALL display a directional indicator (arrow icon or +/- prefix) in addition to color.

#### Scenario: Point transaction displays positive amount

- **WHEN** a point transaction with positive amount is displayed
- **THEN** the display SHALL include both green color AND an upward arrow icon or "+" prefix

#### Scenario: Point transaction displays negative amount

- **WHEN** a point transaction with negative amount is displayed
- **THEN** the display SHALL include both red color AND a downward arrow icon or "-" prefix

### Requirement: Table accessibility markup

All data tables SHALL include `scope="col"` on header cells. Tables that display user data SHALL include either a `<caption>` element or an `aria-label` attribute describing the table's purpose.

#### Scenario: Admin users table renders

- **WHEN** the admin users list page renders a table of users
- **THEN** each `<th>` element SHALL have `scope="col"`
- **THEN** the `<table>` element SHALL have `aria-label` describing it as a user management table

### Requirement: Filter tabs accessibility

Tab-based filter controls (such as submission review status filters) SHALL use WAI-ARIA tab pattern: the container SHALL have `role="tablist"`, each tab SHALL have `role="tab"`, and the active tab SHALL have `aria-selected="true"`.

#### Scenario: Submission review filter tabs render

- **WHEN** the submission review page renders filter tabs (pending, approved, rejected, all)
- **THEN** the tab container SHALL have `role="tablist"`
- **THEN** each filter button SHALL have `role="tab"`
- **THEN** the currently active tab SHALL have `aria-selected="true"`
- **THEN** inactive tabs SHALL have `aria-selected="false"`
