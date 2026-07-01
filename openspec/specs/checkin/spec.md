# checkin Specification

## Purpose

TBD - created by archiving change 'daily-training-submission-system'. Update Purpose after archive.

## Requirements

### Requirement: Student check-in

Students SHALL be able to check in once per day when the check-in window is open. Duplicate check-ins on the same calendar day MUST be rejected. A successful check-in SHALL trigger the configured RewardProviders.

#### Scenario: Successful check-in within window

- **WHEN** a student clicks check-in and the current time is within the active window
- **THEN** the system SHALL record the check-in with a timestamp and trigger RewardProviders

#### Scenario: Check-in outside window rejected

- **WHEN** a student attempts to check in outside the active time window
- **THEN** the system SHALL display an informational message and SHALL NOT record the check-in

#### Scenario: Duplicate check-in rejected

- **WHEN** a student who already checked in today attempts to check in again
- **THEN** the system SHALL display a confirmation of their earlier check-in and SHALL NOT create a duplicate record

<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
-->

---
### Requirement: Global check-in schedule

Teachers SHALL be able to configure a global check-in schedule per class. The schedule MUST specify: active days of the week (list of weekday integers 0-6) and a default time window (start time, end time, or null for all-day).

#### Scenario: Check-in disabled on excluded weekday

- **WHEN** a student attempts to check in on a weekday not in the active days list
- **THEN** the system SHALL reject the check-in with a message indicating check-in is not available today

#### Scenario: All-day window allows any time

- **WHEN** the global schedule has a null time window for the current weekday
- **THEN** the system SHALL accept check-ins at any time during that day

<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
-->

---
### Requirement: Per-day check-in override

Teachers SHALL be able to create a per-day override for a specific calendar date. An override MUST specify active status (enabled/disabled), and optionally a custom time window. The override SHALL take precedence over the global schedule for that specific date.

#### Scenario: Override disables check-in on a normally active day

- **WHEN** an override sets active=false for today
- **THEN** all student check-in attempts SHALL be rejected regardless of the global schedule

#### Scenario: Override extends check-in window

- **WHEN** an override sets a longer time window than the global default for today
- **THEN** students SHALL be able to check in during the extended window

<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
-->

---
### Requirement: Check-in status visibility

Students SHALL be able to see whether check-in is currently open, their check-in status for today, and the closing time of the current window.

#### Scenario: Check-in status shown on dashboard

- **WHEN** a student views their dashboard
- **THEN** the system SHALL display check-in open/closed status and, if open, the closing time

<!-- @trace
source: daily-training-submission-system
updated: 2026-03-18
-->

---
### Requirement: Student performs daily check-in via browser form

The system SHALL accept check-in via `POST /classes/{class_id}/checkin/browser` from browser form submissions. The endpoint SHALL redirect after processing (PRG pattern). The redirect behavior SHALL differ based on outcome:

- **Success**: Record created → redirect to `GET /pages/dashboard` (HTTP 302, no error parameter)
- **Already checked in**: Duplicate attempt → redirect to `GET /pages/dashboard` (HTTP 302, **no error parameter**)
- **Window closed or other error**: → redirect to `GET /pages/dashboard?error=<message>` (HTTP 302, with error parameter)

The "already checked in" state MUST NOT be treated as an error condition in the redirect. It is an expected idempotent state.

#### Scenario: Successful check-in redirects to dashboard

- **WHEN** a student submits the check-in form and the check-in window is open
- **THEN** the system SHALL record the check-in and redirect to `GET /pages/dashboard` (HTTP 302)
- **AND** the redirect SHALL NOT include an `error` query parameter

#### Scenario: Already checked in redirects to dashboard without error

- **WHEN** a student who already checked in today submits the check-in form
- **THEN** the system SHALL redirect to `GET /pages/dashboard` (HTTP 302) without creating a duplicate record
- **AND** the redirect SHALL NOT include an `error` query parameter

#### Scenario: Check-in window closed redirects with error

- **WHEN** a student submits the check-in form outside the check-in window
- **THEN** the system SHALL redirect to `GET /pages/dashboard?error=簽到時間已關閉` (HTTP 302)
- **AND** the redirect SHALL include the `error` query parameter with a descriptive message

<!-- @trace
source: fix-dashboard-and-page-bugs
updated: 2026-03-20
code:
  - src/tasks/checkin/router.py
-->

---
### Requirement: Teacher configures check-in schedule via web UI

Teachers with `MANAGE_OWN_CLASS` or `MANAGE_ALL_CLASSES` permission SHALL be able to view and update their class's check-in schedule through a dedicated web page at `/pages/teacher/classes/{class_id}/checkin-config`. The page SHALL display the current `CheckinConfig` (active weekdays and time window) and allow the teacher to update it by submitting a form that calls `POST /classes/{class_id}/checkin-config`.

#### Scenario: Teacher views current check-in configuration

- **WHEN** a teacher navigates to `/pages/teacher/classes/{class_id}/checkin-config`
- **THEN** the page displays the currently configured active weekdays
- **AND** the page displays the currently configured window start and end times (if set)
- **AND** if no config exists, sensible defaults are shown (all weekdays, no time restriction)

#### Scenario: Teacher updates active weekdays

- **WHEN** a teacher selects weekdays and submits the configuration form
- **THEN** `POST /classes/{class_id}/checkin-config` is called with the selected weekdays
- **AND** the page reloads with a success message confirming the update

<!-- @trace
source: task-scheduling-and-checkin
updated: 2026-03-19
-->

---
### Requirement: Teacher sets a single-day check-in override via web UI

Teachers SHALL be able to add a single-day override (activate or deactivate check-in for a specific date, with optional custom time window) through the check-in config page without leaving the browser.

#### Scenario: Teacher disables check-in for a specific date

- **WHEN** a teacher enters a date, sets `active: false`, and submits the override form on the config page
- **THEN** `POST /classes/{class_id}/checkin-overrides` is called with the date and `active: false`
- **AND** students cannot check in on that date even if the weekday is normally active

<!-- @trace
source: task-scheduling-and-checkin
updated: 2026-03-19
-->

---
### Requirement: Teacher accesses attendance management from points manage page

The points management page (`/pages/teacher/classes/{class_id}/points`) SHALL include a link or navigation entry to the attendance management page (`/pages/teacher/classes/{class_id}/attendance`). The existing generic point deduction form SHALL NOT be the sole mechanism for handling check-in exceptions.

#### Scenario: Points manage page links to attendance management

- **WHEN** a teacher views the points management page
- **THEN** the page SHALL display a clearly labeled link or card navigating to the attendance management page for the same class

<!-- @trace
source: task-review-attendance-dashboard
updated: 2026-03-22
code:
  - src/templates/student/dashboard.html
  - src/gamification/points/models.py
  - src/templates/student/learning_history.html
  - src/tasks/checkin/models.py
  - src/tasks/checkin/router.py
  - src/tasks/submissions/models.py
  - src/templates/shared/base.html
  - src/templates/teacher/points_manage.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/student/submit_task.html
  - src/templates/student/class_history.html
  - src/tasks/submissions/service.py
  - src/pages/router.py
  - src/main.py
  - src/tasks/submissions/router.py
  - src/templates/teacher/submission_review.html
  - src/templates/student/submission_rejection.html
  - src/community/feed/models.py
tests:
  - tests/test_submission_approval.py
  - tests/test_resubmission.py
  - tests/test_attendance_management.py
  - tests/test_pages.py
  - tests/test_submissions.py
-->

---
### Requirement: Check-in endpoint validates class membership

The system SHALL verify that the student is a member of the target class before recording a check-in. Non-members SHALL be rejected with HTTP 403.

#### Scenario: Non-member check-in rejected

- **WHEN** a student who is not a member of the class attempts to check in via `POST /classes/{class_id}/checkin` or `POST /classes/{class_id}/checkin/browser`
- **THEN** the system SHALL return HTTP 403 and SHALL NOT create a check-in record

#### Scenario: Member check-in proceeds normally

- **WHEN** a student who is a member of the class attempts to check in
- **THEN** the system SHALL proceed with check-in processing as normal

<!-- @trace
source: security-audit-fixes
updated: 2026-03-23
code:
  - src/tasks/checkin/service.py
  - src/tasks/checkin/router.py
tests:
  - tests/test_security_audit.py
-->

---
### Requirement: Checkin config endpoints validate class ownership

The check-in configuration endpoints (`POST /classes/{class_id}/checkin-config` and `POST /classes/{class_id}/checkin-overrides`) SHALL verify that the requesting user is either a teacher-member of the target class or holds the `MANAGE_ALL_CLASSES` permission. Users who hold `MANAGE_OWN_CLASS` but are not a teacher-member of the specific class SHALL be rejected with HTTP 403.

#### Scenario: Teacher of a different class cannot configure checkin

- **WHEN** a user with `MANAGE_OWN_CLASS` permission who is NOT a teacher-member of the target class attempts to configure its check-in settings
- **THEN** the system SHALL return HTTP 403

#### Scenario: Teacher of the class can configure checkin

- **WHEN** a user with `MANAGE_OWN_CLASS` permission who IS a teacher-member of the target class configures check-in settings
- **THEN** the system SHALL accept the request and update the configuration

#### Scenario: Global class manager can configure any class checkin

- **WHEN** a user with `MANAGE_ALL_CLASSES` permission configures check-in settings for any class
- **THEN** the system SHALL accept the request regardless of class membership

<!-- @trace
source: security-audit-fixes
updated: 2026-03-23
code:
  - src/tasks/checkin/service.py
  - src/tasks/checkin/router.py
tests:
  - tests/test_security_audit.py
-->

---
### Requirement: Teacher corrects attendance

Teachers SHALL be able to correct attendance records for students in classes they manage. The `POST /api/classes/{class_id}/attendance/correct` endpoint SHALL call `can_manage_class(user, cls)` to verify the teacher has authority over the specified class. If the teacher cannot manage the class, the system SHALL return HTTP 403. Teachers with `MANAGE_ALL_CLASSES` SHALL be able to correct attendance in any class.

#### Scenario: Teacher corrects attendance in own class

- **WHEN** a teacher who manages class C calls `POST /api/classes/{class_id}/attendance/correct` for class C
- **THEN** the system SHALL proceed with the correction normally

#### Scenario: Teacher corrects attendance in another class

- **WHEN** a teacher who does NOT manage class C calls `POST /api/classes/{class_id}/attendance/correct` for class C
- **THEN** the system SHALL return HTTP 403

<!-- @trace
source: fix-cross-class-access-control
updated: 2026-03-24
-->

---
### Requirement: Attendance page enforces class management

The teacher attendance page `GET /pages/teacher/classes/{class_id}/attendance` SHALL verify the caller manages the requested class via `can_manage_class()`, not merely that the caller holds a class-management permission flag. A teacher who does not manage the class SHALL receive HTTP 403 before the roster or attendance data is loaded or rendered.

#### Scenario: Non-managing teacher opens another class's attendance page

- **WHEN** a teacher who does not manage the class requests its attendance page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose the roster or attendance state

#### Scenario: Managing teacher opens their own attendance page

- **WHEN** a teacher who manages the class requests its attendance page
- **THEN** the system SHALL load and render the attendance roster
