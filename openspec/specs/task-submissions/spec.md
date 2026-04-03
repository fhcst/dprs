## ADDED Requirements

### Requirement: TaskSubmission stores review state

The `TaskSubmission` document SHALL include the following review-related fields:
- `status`: `"pending" | "approved" | "rejected"` — defaults to `"pending"` on creation
- `rejection_reason`: `str | None` — set when status is `"rejected"`
- `resubmit_deadline`: `datetime | None` — optional deadline set by teacher on rejection
- `parent_submission_id`: `str | None` — set on resubmissions to reference the rejected predecessor

#### Scenario: New submissions have pending status

- **WHEN** a student submits a task
- **THEN** `status` SHALL be `"pending"`, `rejection_reason` SHALL be null, `resubmit_deadline` SHALL be null, and `parent_submission_id` SHALL be null

#### Scenario: Rejection fields populated on reject

- **WHEN** a teacher rejects a submission
- **THEN** `status` SHALL be `"rejected"`, `rejection_reason` SHALL contain the reason text, and `resubmit_deadline` SHALL contain the deadline if provided

#### Scenario: Parent link set on resubmission

- **WHEN** a student creates a resubmission for a previously rejected submission
- **THEN** the new submission's `parent_submission_id` SHALL equal the rejected submission's document ID

## MODIFIED Requirements

### Requirement: Student submits daily task

Students SHALL be able to submit the daily task assigned to the current date in a class they belong to. Each student MUST have at most one non-rejected submission per template-date assignment. Submissions with `status: "rejected"` SHALL NOT count toward the uniqueness constraint, allowing resubmission. The submission MUST capture a snapshot of the template version at submission time. On creation, `status` SHALL default to `"pending"` and points SHALL be awarded immediately.

#### Scenario: Successful first submission

- **WHEN** a student submits a completed form for today's template
- **THEN** the system SHALL persist the submission with `status: "pending"`, a timestamp, and trigger the configured RewardProviders

#### Scenario: Duplicate submission rejected when active submission exists

- **WHEN** a student attempts to submit a second time for the same template-date and a non-rejected submission already exists
- **THEN** the system SHALL return an error and SHALL NOT create a duplicate submission

#### Scenario: Resubmission allowed after rejection

- **WHEN** a student submits for a date where their only existing submission has `status: "rejected"`
- **THEN** the system SHALL allow the new submission and SHALL NOT return a duplicate error

The `TaskSubmission` document SHALL include the following review-related fields:
- `status`: `"pending" | "approved" | "rejected"` — defaults to `"pending"` on creation
- `rejection_reason`: `str | None` — set when status is `"rejected"`
- `resubmit_deadline`: `datetime | None` — optional deadline set by teacher on rejection
- `parent_submission_id`: `str | None` — set on resubmissions to reference the rejected predecessor

#### Scenario: New submissions have pending status

- **WHEN** a student submits a task
- **THEN** `status` SHALL be `"pending"`, `rejection_reason` SHALL be null, `resubmit_deadline` SHALL be null, and `parent_submission_id` SHALL be null

#### Scenario: Rejection fields populated on reject

- **WHEN** a teacher rejects a submission
- **THEN** `status` SHALL be `"rejected"`, `rejection_reason` SHALL contain the reason text, and `resubmit_deadline` SHALL contain the deadline if provided

#### Scenario: Parent link set on resubmission

- **WHEN** a student creates a resubmission for a previously rejected submission
- **THEN** the new submission's `parent_submission_id` SHALL equal the rejected submission's document ID

## ADDED Requirements


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

### Requirement: Student can view learning history with review status

Students SHALL be able to view their own past submissions including the review status. The history page SHALL display `status`, `rejection_reason`, and a link to the rejection detail page for `"rejected"` submissions.

#### Scenario: History shows review status

- **WHEN** a student views their learning history
- **THEN** each submission SHALL display its current `status` (pending / approved / rejected)

#### Scenario: Rejected submission shows link to detail

- **WHEN** a submission in the history has `status: "rejected"`
- **THEN** the page SHALL display the rejection reason and a link to `GET /pages/student/submissions/{submission_id}/rejection`

## Requirements


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

### Requirement: Student can view learning history with review status

Students SHALL be able to view their own past submissions including the review status. The history page SHALL display `status`, `rejection_reason`, and a link to the rejection detail page for `"rejected"` submissions.

#### Scenario: History shows review status

- **WHEN** a student views their learning history
- **THEN** each submission SHALL display its current `status` (pending / approved / rejected)

#### Scenario: Rejected submission shows link to detail

- **WHEN** a submission in the history has `status: "rejected"`
- **THEN** the page SHALL display the rejection reason and a link to `GET /pages/student/submissions/{submission_id}/rejection`
## ADDED Requirements

### Requirement: Submission endpoint validates class membership

The system SHALL verify that the submitting student is a member of the target class before processing a task submission. Non-members SHALL be rejected with HTTP 403.

#### Scenario: Non-member student submission rejected

- **WHEN** a student who is not a member of the class submits a task to `POST /classes/{class_id}/submissions`
- **THEN** the system SHALL return HTTP 403 and SHALL NOT create a submission record

#### Scenario: Member student submission proceeds normally

- **WHEN** a student who is a member of the class submits a task
- **THEN** the system SHALL proceed with the submission as normal

<!-- @trace
source: security-audit-fixes
updated: 2026-03-23
code:
  - src/tasks/submissions/service.py
  - src/tasks/submissions/router.py
tests:
  - tests/test_security_audit.py
-->

### Requirement: Student submit page validates class membership before rendering

The system SHALL verify that the current student is a member of the target class before rendering `GET /pages/student/classes/{class_id}/submit`. The page MUST NOT reveal the current day's template, rejected-submission state, or class-specific empty-state messages to users who are not members of that class.

#### Scenario: Class member can open the submit page

- **WHEN** an authenticated student who belongs to class C requests `GET /pages/student/classes/{class_id}/submit` for class C
- **THEN** the system SHALL render the submit page normally using that class's current task state

#### Scenario: Non-member is rejected before class task details are revealed

- **WHEN** an authenticated user who is not a member of class C requests `GET /pages/student/classes/{class_id}/submit` for class C
- **THEN** the system SHALL return HTTP 403
- **AND** the response SHALL NOT reveal whether class C has a task template for today
- **AND** the response SHALL NOT reveal rejected-submission state for that class

#### Scenario: Member sees the empty state only for their own class

- **WHEN** an authenticated student who belongs to class C requests `GET /pages/student/classes/{class_id}/submit` for class C and no template is assigned for today
- **THEN** the system SHALL render the submit page with the "no task today" empty state

<!-- @trace
source: fix-submit-page-membership-check
updated: 2026-04-04
code:
  - src/pages/router.py
tests:
  - tests/test_pages.py
-->
