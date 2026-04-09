# design-tokens Specification

## Purpose

TBD - created by archiving change 'uiux-audit-remediation'. Update Purpose after archive.

## Requirements

### Requirement: Button visual hierarchy

The system SHALL maintain a clear visual distinction between primary CTA buttons, secondary buttons, and active tab indicators. Primary CTA buttons SHALL use `bg-brand-600` with `rounded-lg`. Active filter tabs SHALL use a visually distinct style (such as `bg-brand-100 text-brand-700 border-brand-300`) that is clearly different from primary CTA buttons.

#### Scenario: Submission review page displays tabs and approve button

- **WHEN** the submission review page renders with active filter tabs and approve buttons
- **THEN** the active tab style SHALL be visually distinct from the approve CTA button
- **THEN** a user SHALL be able to distinguish tabs from action buttons at a glance


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
### Requirement: Content max-width constraint

All page content areas (excluding admin tables that require full width) SHALL be constrained to a maximum width. Content-heavy pages (submission review, class history, learning history, points management) SHALL use `max-w-5xl` or narrower. Form pages SHALL use `max-w-3xl` or narrower.

#### Scenario: Submission review page on a 1920px monitor

- **WHEN** the submission review page renders on a 1920px wide viewport
- **THEN** the content area SHALL NOT exceed the defined max-width
- **THEN** the content SHALL be horizontally centered within the viewport


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
### Requirement: Mobile body text minimum size

On viewports narrower than 640px, primary body text SHALL be at least 16px (`text-base` in Tailwind). Secondary/meta text (timestamps, muted labels) SHALL be at least 14px (`text-sm`).

#### Scenario: Student reads task description on mobile

- **WHEN** a student views a task description on a viewport narrower than 640px
- **THEN** the body text font size SHALL be at least 16px


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
### Requirement: Consistent card styling

All card components across the system SHALL use consistent styling: `rounded-xl` border radius, `border border-gray-200 dark:border-gray-800`, and `p-5` padding. The login page card SHALL follow the same radius (`rounded-xl`, not `rounded-2xl`).

#### Scenario: Dashboard stat cards render

- **WHEN** dashboard stat cards render
- **THEN** each card SHALL use `rounded-xl` border radius and consistent padding


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
### Requirement: Consistent success color

All success indicators throughout the system SHALL use the `green` color palette (not `emerald`). This applies to success banners, check-in badges, approved status badges, and positive point indicators.

#### Scenario: Settings page shows success message

- **WHEN** a user successfully updates their display name on the settings page
- **THEN** the success banner SHALL use `green-50`/`green-700` colors (not emerald)


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
### Requirement: Terminology standardization

All user-facing text SHALL use consistent terminology: "任務" (not "作業") for tasks/assignments, and "通過" (not "確認") for the approval action. The submission review filter tab for approved items SHALL read "已通過".

#### Scenario: Submission review page displays filter tabs

- **WHEN** the submission review page renders
- **THEN** the approved filter tab SHALL read "已通過" (not "已確認")

#### Scenario: Dashboard displays teacher tool links

- **WHEN** the teacher dashboard renders class cards with tool links
- **THEN** the submission review link SHALL read "任務審閱" (not "作業審閱")

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