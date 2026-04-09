## ADDED Requirements

### Requirement: Unified empty state component

The system SHALL provide a Jinja2 macro for rendering empty states. The macro SHALL accept parameters for icon (SVG markup), title, description, and optional CTA button (text + href). All pages that can display an empty list SHALL use this macro.

#### Scenario: Dashboard renders with no classes (student)

- **WHEN** a student with no class memberships views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未加入任何班級", a description "向老師索取邀請碼，或搜尋公開班級", and a "加入班級" CTA button

#### Scenario: Dashboard renders with no classes (teacher)

- **WHEN** a teacher with no classes views the dashboard
- **THEN** the empty state SHALL display an icon, the title "尚未建立任何班級", a description "建立您的第一個班級，開始管理學生每日練習", and a "建立班級" CTA button

#### Scenario: Submission review page has no submissions

- **WHEN** a teacher views the submission review page and there are no submissions for the selected date
- **THEN** the empty state SHALL display an icon and the message "今天沒有待審作業，學生提交後會顯示在這裡"

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
