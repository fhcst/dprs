# empty-states Specification

## Purpose

TBD - created by archiving change 'uiux-audit-remediation'. Update Purpose after archive.

## Requirements

### Requirement: Unified empty state component

The system SHALL provide a Jinja2 macro for rendering empty states. The macro SHALL accept parameters for icon (SVG markup), title, description, and optional CTA button (text + href). All pages that can display an empty list SHALL use this macro.

The macro SHALL render the `icon` argument as raw, un-escaped HTML so that SVG markup is displayed as a vector image and NOT as escaped source text. Because the rendering environment has Jinja2 autoescape enabled, the macro MUST apply the `| safe` filter to the `icon` argument to bypass escaping.

The `icon` argument MUST be restricted to trusted, static markup (such as an SVG string literal hard-coded in a template). Callers MUST NOT pass user-controlled or otherwise untrusted data as `icon`, because raw rendering of untrusted input would cause cross-site scripting (XSS). The macro SHALL document this restriction in an inline comment.

All other text parameters (`title`, `description`, `cta_text`, `cta_href`) SHALL remain HTML-escaped by autoescape and MUST NOT use the `| safe` filter.

#### Scenario: Icon SVG markup renders as a vector image

- **WHEN** a caller invokes the macro with `icon` set to a static SVG string literal and the page is rendered
- **THEN** the rendered HTML SHALL contain the SVG element as live markup and SHALL NOT contain escaped `&lt;svg&gt;` source text

#### Scenario: Icon argument is trusted static markup only

- **WHEN** any of the macro's callers supplies the `icon` argument
- **THEN** the supplied value SHALL be a hard-coded static SVG literal defined in the template and SHALL NOT be user-controlled input

#### Scenario: Non-icon text parameters stay escaped

- **WHEN** the macro renders `title`, `description`, `cta_text`, or `cta_href`
- **THEN** those values SHALL be HTML-escaped by autoescape and SHALL NOT be passed through the `| safe` filter

#### Scenario: Dashboard renders with no classes (student)

- **WHEN** a student with no class memberships views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未加入任何班級", a description "向老師索取邀請碼，或搜尋公開班級", and a "加入班級" CTA button

#### Scenario: Dashboard renders with no classes (teacher)

- **WHEN** a teacher with no classes views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未建立任何班級", a description "建立您的第一個班級，開始管理學生每日練習", and a "建立班級" CTA button

#### Scenario: Submission review page has no submissions

- **WHEN** a teacher views the submission review page and there are no submissions for the selected date
- **THEN** the empty state SHALL display an icon and the message "今天沒有待審作業，學生提交後會顯示在這裡"


<!-- @trace
source: fix-empty-state-icon
updated: 2026-06-29
code:
  - src/templates/shared/macros.html
  - docs/security-notes.md
-->

---
### Requirement: Teacher dashboard pending actions

The teacher dashboard SHALL display a pending actions summary section showing: the total count of pending submissions across all classes, and the count of unreviewed join requests. Each count SHALL link to the relevant management page.

#### Scenario: Teacher has pending submissions

- **WHEN** a teacher with 5 pending submissions across 2 classes views the dashboard
- **THEN** the dashboard SHALL display "5 份待審作業" with a link to the submission review page

#### Scenario: Teacher has pending join requests

- **WHEN** a teacher with 3 unreviewed join requests views the dashboard
- **THEN** the dashboard SHALL display "3 個加入申請待處理" with a link to the members management page

#### Scenario: Teacher has no pending items

- **WHEN** a teacher with no pending submissions and no pending join requests views the dashboard
- **THEN** the pending actions section SHALL display a checkmark icon and "所有事項已處理完畢"


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
### Requirement: First-time user welcome message

When a user logs in for the first time (no prior submissions, no class memberships, and first login within 24 hours of account creation), the dashboard SHALL display a welcome message with quick-start guidance appropriate to the user's role.

#### Scenario: New student first login

- **WHEN** a newly created student account logs in for the first time
- **THEN** the dashboard SHALL display a welcome card with the title "歡迎加入！" and a step-by-step guide: "1. 加入班級 → 2. 完成每日任務 → 3. 獲得積分和徽章"

#### Scenario: New teacher first login

- **WHEN** a newly created teacher account logs in for the first time
- **THEN** the dashboard SHALL display a welcome card with the title "歡迎！開始設定您的班級" and a step-by-step guide: "1. 建立班級 → 2. 邀請學生 → 3. 建立任務模板"

#### Scenario: Returning user login

- **WHEN** a user who has previously submitted tasks or has class memberships logs in
- **THEN** the welcome message SHALL NOT be displayed

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