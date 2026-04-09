# tailwind-build Specification

## Purpose

TBD - created by archiving change 'uiux-audit-remediation'. Update Purpose after archive.

## Requirements

### Requirement: Static CSS generation

The system SHALL generate a static CSS file from Tailwind configuration at build time. The base template SHALL reference this static CSS file instead of the Tailwind Play CDN script. The Tailwind configuration (colors, fonts, dark mode strategy) SHALL produce identical styling to the current Play CDN configuration.

#### Scenario: Page loads in production

- **WHEN** any page loads in the production environment
- **THEN** the page SHALL load a static CSS file (not the Tailwind Play CDN script)
- **THEN** the page SHALL render identically to the current CDN-based rendering

#### Scenario: Developer adds new Tailwind classes

- **WHEN** a developer adds new Tailwind CSS classes to a template file
- **THEN** the build process SHALL detect the new classes and regenerate the CSS file
- **THEN** the new classes SHALL be included in the output CSS


<!-- @trace
source: uiux-audit-remediation
updated: 2026-04-09
code:
  - src/templates/student/badges.html
  - src/templates/shared/macros.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/badges_manage.html
  - src/templates/login.html
  - src/templates/student/class_history.html
  - src/templates/teacher/submission_review.html
  - src/templates/community/feed.html
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/teacher/templates_list.html
  - src/templates/settings.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/shared/base.html
  - src/templates/teacher/points_manage.html
  - src/pages/router.py
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - Dockerfile
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - src/main.py
  - docs/uiux-audit/20260408/00-index.md
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - src/static/css/input.css
  - src/templates/admin/users_list.html
  - src/templates/setup.html
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/student/learning_history.html
  - src/templates/teacher/class_hub.html
  - src/templates/community/leaderboard.html
  - src/static/css/tailwind.css
tests:
  - tests/test_admin_users.py
  - tests/test_class_hub_page.py
  - tests/test_dashboard_and_page_bugs.py
-->

---
### Requirement: Tailwind configuration extraction

The Tailwind configuration (custom colors, font families, dark mode class strategy) currently inline in `base.html` SHALL be extracted to a standalone `tailwind.config.js` file. The `base.html` inline configuration script SHALL be removed.

#### Scenario: Tailwind config file is created

- **WHEN** the build system processes templates
- **THEN** the `tailwind.config.js` file SHALL contain the brand color palette, font family definitions, and `darkMode: 'class'` setting
- **THEN** the `base.html` SHALL NOT contain an inline Tailwind config script


<!-- @trace
source: uiux-audit-remediation
updated: 2026-04-09
code:
  - src/templates/student/badges.html
  - src/templates/shared/macros.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/badges_manage.html
  - src/templates/login.html
  - src/templates/student/class_history.html
  - src/templates/teacher/submission_review.html
  - src/templates/community/feed.html
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/teacher/templates_list.html
  - src/templates/settings.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/shared/base.html
  - src/templates/teacher/points_manage.html
  - src/pages/router.py
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - Dockerfile
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - src/main.py
  - docs/uiux-audit/20260408/00-index.md
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - src/static/css/input.css
  - src/templates/admin/users_list.html
  - src/templates/setup.html
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/student/learning_history.html
  - src/templates/teacher/class_hub.html
  - src/templates/community/leaderboard.html
  - src/static/css/tailwind.css
tests:
  - tests/test_admin_users.py
  - tests/test_class_hub_page.py
  - tests/test_dashboard_and_page_bugs.py
-->

---
### Requirement: Touch target minimum size

All interactive elements (buttons, links, form controls) SHALL have a minimum touch target size of 44x44 CSS pixels. Elements that are currently smaller SHALL have their padding increased to meet this minimum.

#### Scenario: Feed post delete button renders on mobile

- **WHEN** the feed post delete button renders on a touch device
- **THEN** the button's clickable area SHALL be at least 44x44 CSS pixels

#### Scenario: Reaction button renders on mobile

- **WHEN** the feed reaction ("讚") button renders on a touch device
- **THEN** the button's clickable area SHALL be at least 44x44 CSS pixels


<!-- @trace
source: uiux-audit-remediation
updated: 2026-04-09
code:
  - src/templates/student/badges.html
  - src/templates/shared/macros.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/badges_manage.html
  - src/templates/login.html
  - src/templates/student/class_history.html
  - src/templates/teacher/submission_review.html
  - src/templates/community/feed.html
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/teacher/templates_list.html
  - src/templates/settings.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/shared/base.html
  - src/templates/teacher/points_manage.html
  - src/pages/router.py
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - Dockerfile
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - src/main.py
  - docs/uiux-audit/20260408/00-index.md
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - src/static/css/input.css
  - src/templates/admin/users_list.html
  - src/templates/setup.html
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/student/learning_history.html
  - src/templates/teacher/class_hub.html
  - src/templates/community/leaderboard.html
  - src/static/css/tailwind.css
tests:
  - tests/test_admin_users.py
  - tests/test_class_hub_page.py
  - tests/test_dashboard_and_page_bugs.py
-->

---
### Requirement: Toast UI Editor mobile preview mode

On viewports narrower than 640px, the Toast UI Editor SHALL use `tab` preview style (write/preview toggle) instead of `vertical` (side-by-side split).

#### Scenario: Student opens task submission form on mobile

- **WHEN** a student opens the task submission form on a viewport narrower than 640px
- **THEN** the markdown editor SHALL render in tab mode (write/preview toggle)
- **THEN** each panel SHALL occupy the full editor width

#### Scenario: Student opens task submission form on desktop

- **WHEN** a student opens the task submission form on a viewport 640px or wider
- **THEN** the markdown editor SHALL render in vertical (side-by-side) mode

<!-- @trace
source: uiux-audit-remediation
updated: 2026-04-09
code:
  - src/templates/student/badges.html
  - src/templates/shared/macros.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/badges_manage.html
  - src/templates/login.html
  - src/templates/student/class_history.html
  - src/templates/teacher/submission_review.html
  - src/templates/community/feed.html
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/teacher/templates_list.html
  - src/templates/settings.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/shared/base.html
  - src/templates/teacher/points_manage.html
  - src/pages/router.py
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - Dockerfile
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - src/main.py
  - docs/uiux-audit/20260408/00-index.md
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - src/static/css/input.css
  - src/templates/admin/users_list.html
  - src/templates/setup.html
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - src/core/users/router.py
  - src/templates/student/dashboard.html
  - src/templates/student/learning_history.html
  - src/templates/teacher/class_hub.html
  - src/templates/community/leaderboard.html
  - src/static/css/tailwind.css
tests:
  - tests/test_admin_users.py
  - tests/test_class_hub_page.py
  - tests/test_dashboard_and_page_bugs.py
-->

---
### Requirement: Tailwind CSS output classified as build artifact

The `src/static/css/tailwind.css` file SHALL be listed in `.gitignore` to prevent accidental commits of the build output. The file SHALL be generated by either the local `scripts/build-css.sh` script during development or by the Dockerfile's Tailwind build step during Docker image construction.

#### Scenario: tailwind.css is gitignored

- **WHEN** a developer runs `git status` after building CSS locally
- **THEN** `src/static/css/tailwind.css` SHALL NOT appear as an untracked or modified file

#### Scenario: Docker build generates tailwind.css

- **WHEN** `docker build` is executed
- **THEN** the Dockerfile SHALL generate `src/static/css/tailwind.css` from `src/static/css/input.css` using the Tailwind standalone CLI
- **THEN** the generated CSS SHALL include all utility classes referenced in `src/templates/**/*.html`

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