# submission-approval Specification

## Purpose

TBD - created by archiving change 'task-review-attendance-dashboard'. Update Purpose after archive.

## Requirements

### Requirement: Teacher approves a task submission

Teachers with `MANAGE_TASKS` permission SHALL be able to approve a `TaskSubmission` by calling `POST /api/submissions/{submission_id}/approve`. The system SHALL verify that the teacher can manage the class the submission belongs to by calling `can_manage_class(user, cls)` before proceeding. If the teacher cannot manage the class, the system SHALL return HTTP 403. Approval SHALL set `status` to `"approved"`. If the submission was previously `"rejected"`, approval SHALL also create a positive `PointTransaction` to restore the revoked points (source_event: `"submission_reapproved"`).

#### Scenario: Teacher approves a pending submission

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/approve` on a pending submission in a class they manage
- **THEN** the system SHALL set `status` to `"approved"` and return HTTP 200

#### Scenario: Teacher approves a previously rejected submission

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/approve` on a rejected submission in a class they manage
- **THEN** the system SHALL set `status` to `"approved"`
- **AND** the system SHALL create a positive `PointTransaction` equal to the class `submission_points` with `source_event: "submission_reapproved"`

#### Scenario: Teacher approves submission in another class

- **WHEN** a teacher with `MANAGE_TASKS` but no membership in class C calls `POST /api/submissions/{submission_id}/approve` for a submission in class C
- **THEN** the system SHALL return HTTP 403

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

<!-- @trace
source: fix-cross-class-access-control
updated: 2026-03-24
-->

---
### Requirement: Teacher rejects a task submission

Teachers with `MANAGE_TASKS` permission SHALL be able to reject a `TaskSubmission` by calling `POST /api/submissions/{submission_id}/reject` with a required `rejection_reason` (string) and optional `resubmit_deadline` (ISO 8601 datetime, nullable). The system SHALL verify that the teacher can manage the class the submission belongs to before proceeding. If the teacher cannot manage the class, the system SHALL return HTTP 403. Rejection SHALL set `status` to `"rejected"`, store the reason and deadline, and create a negative `PointTransaction` equal to the class `submission_points` (source_event: `"submission_rejected"`).

#### Scenario: Teacher rejects a submission with reason

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/reject` with a valid `rejection_reason` for a submission in a class they manage
- **THEN** the system SHALL set `status` to `"rejected"`, store `rejection_reason` and `resubmit_deadline`
- **AND** the system SHALL create a negative `PointTransaction` equal to `submission_points`

#### Scenario: Rejection without reason is rejected

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/reject` with an empty `rejection_reason`
- **THEN** the system SHALL return HTTP 422 and SHALL NOT change the submission status

#### Scenario: Teacher rejects an already-approved submission

- **WHEN** a teacher rejects a submission with `status: "approved"`
- **THEN** the system SHALL set `status` to `"rejected"` and create a negative `PointTransaction`
- **AND** the prior approval SHALL be superseded

#### Scenario: Teacher rejects submission in another class

- **WHEN** a teacher with `MANAGE_TASKS` but no membership in class C calls `POST /api/submissions/{submission_id}/reject` for a submission in class C
- **THEN** the system SHALL return HTTP 403

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

<!-- @trace
source: fix-cross-class-access-control
updated: 2026-03-24
-->

---
### Requirement: Student views rejection detail page

The system SHALL provide a page at `GET /pages/student/submissions/{submission_id}/rejection` that displays the rejection reason, optional resubmit deadline, and original submission content. The page SHALL be accessible only to the owning student.

#### Scenario: Student views rejection detail

- **WHEN** a student navigates to the rejection detail page for a rejected submission
- **THEN** the page SHALL display the rejection reason, resubmit deadline (if set), and the original field values

#### Scenario: Non-owner cannot access rejection detail

- **WHEN** a different student or unauthorized user accesses the rejection page
- **THEN** the system SHALL return HTTP 403

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
### Requirement: Student resubmits a rejected task

A student whose submission has been rejected SHALL be able to submit a new task for the same date if a `resubmit_deadline` was set and has not passed. The resubmission SHALL be a new `TaskSubmission` document with `parent_submission_id` pointing to the rejected submission. The new submission SHALL trigger points and reward providers as normal.

#### Scenario: Student resubmits within deadline

- **WHEN** a student submits a task for a date where they have a rejected submission with a future `resubmit_deadline`
- **THEN** the system SHALL create a new `TaskSubmission` with `parent_submission_id` set to the rejected submission's ID
- **AND** the system SHALL award points as normal

#### Scenario: Duplicate-submission guard ignores rejected records

- **WHEN** a student attempts to submit for a date where they have only a `"rejected"` submission
- **THEN** the system SHALL allow the new submission (SHALL NOT treat the rejected record as a duplicate)

#### Scenario: No resubmit when deadline has passed or was not set

- **WHEN** a student attempts to submit for a date where their submission was rejected with no deadline or a passed deadline
- **THEN** the system SHALL display a message that resubmission is not available and SHALL NOT create a new submission

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
### Requirement: Student sees submission review status in activity feed

The system SHALL display task approval events in the student's activity feed. When a submission transitions to `"approved"` or `"rejected"`, a corresponding feed entry SHALL be created or surfaced so the student can see the outcome.

#### Scenario: Approved submission appears in feed

- **WHEN** a teacher approves a student's submission
- **THEN** a feed entry with event type `"submission_approved"` SHALL be visible to that student

#### Scenario: Rejected submission appears in feed

- **WHEN** a teacher rejects a student's submission
- **THEN** a feed entry with event type `"submission_rejected"` SHALL be visible to that student
- **AND** the feed entry SHALL link to the rejection detail page

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
