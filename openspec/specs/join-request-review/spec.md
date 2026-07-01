# join-request-review Specification

## Purpose

TBD - created by archiving change 'invite-code-join-review'. Update Purpose after archive.

## Requirements

### Requirement: JoinRequest data model

The system SHALL maintain a `JoinRequest` Beanie Document in the `join_requests` MongoDB collection with the following fields: `class_id` (str), `user_id` (str), `status` (literal: "pending", "approved", "rejected"), `requested_at` (datetime, defaults to UTC now), `reviewed_at` (datetime, nullable), `reviewed_by` (str, nullable), and `invite_code_used` (str). The collection MUST have a partial unique index on `(class_id, user_id)` where `status = "pending"` to ensure only one pending request per student per class.

#### Scenario: Only one pending request per student per class

- **WHEN** a student already has a pending `JoinRequest` for class C and submits another join request for class C
- **THEN** the system MUST reject the request with an error indicating a pending request already exists

#### Scenario: Student can reapply after previous request was resolved

- **WHEN** a student has only approved or rejected `JoinRequest` records for class C (no pending) and the cooldown period has passed
- **THEN** the system SHALL allow the student to create a new `JoinRequest` for class C


<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->

---
### Requirement: Student submits join request via invite code

A student SHALL be able to submit a join request by providing a valid invite code via `POST /classes/join-request`. The endpoint MUST verify that the invite code corresponds to an existing class, that the student is not already a member of that class, that the student does not already have a pending request for that class, and that any rejection cooldown period has elapsed. Only users with identity tag `student` SHALL be permitted to submit join requests. On success, the system SHALL create a `JoinRequest` with status `pending`.

#### Scenario: Successful join request submission

- **WHEN** a student with identity tag `student` submits a valid invite code for class C, is not a member of C, has no pending request for C, and is not within a rejection cooldown period
- **THEN** the system SHALL create a `JoinRequest` with `class_id` = C, `user_id` = student's ID, `status` = "pending", `invite_code_used` = the submitted code, and return a success response

#### Scenario: Invalid invite code

- **WHEN** a student submits an invite code that does not match any class
- **THEN** the system MUST return HTTP 400 with a message indicating the invite code is invalid

#### Scenario: Student already a member

- **WHEN** a student submits a valid invite code for a class they already belong to
- **THEN** the system MUST return HTTP 400 with a message indicating they are already a member

#### Scenario: Duplicate pending request

- **WHEN** a student submits a valid invite code for a class where they already have a pending `JoinRequest`
- **THEN** the system MUST return HTTP 400 with a message indicating a pending request already exists

#### Scenario: Within rejection cooldown period

- **WHEN** a student submits a valid invite code for a class where their most recent `JoinRequest` was rejected and the time elapsed since `reviewed_at` is less than `SystemConfig.join_request_reject_cooldown_hours`
- **THEN** the system MUST return HTTP 400 with a message indicating they must wait before reapplying

#### Scenario: Cooldown disabled

- **WHEN** `SystemConfig.join_request_reject_cooldown_hours` is set to `0` and a student reapplies after rejection
- **THEN** the system SHALL allow the new join request regardless of when the previous rejection occurred

#### Scenario: Non-student user attempts to submit

- **WHEN** a user without identity tag `student` submits a join request
- **THEN** the system MUST return HTTP 403


<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->

---
### Requirement: Rate limiting on join request endpoint

The `POST /classes/join-request` endpoint MUST enforce a rate limit of 5 requests per minute per IP address. Requests exceeding the limit MUST be rejected with HTTP 429.

#### Scenario: Requests within rate limit succeed

- **WHEN** a student sends up to 5 join requests within one minute from the same IP
- **THEN** all requests SHALL be processed normally (subject to other validation)

#### Scenario: Requests exceeding rate limit are rejected

- **WHEN** a student sends a 6th join request within one minute from the same IP
- **THEN** the system MUST return HTTP 429


<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->

---
### Requirement: Teacher views pending join requests

An authorized class manager SHALL be able to view pending join requests for their class via `GET /classes/{class_id}/join-requests`. The endpoint MUST require `can_manage_class` authorization. The response SHALL include each pending request's ID, student user information, `requested_at` timestamp, and `invite_code_used`.

#### Scenario: Teacher views pending requests for their class

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/join-requests` for a class they manage
- **THEN** the system SHALL return a list of all `JoinRequest` records with `status = "pending"` for that class, including student information

#### Scenario: No pending requests

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/join-requests` and there are no pending requests
- **THEN** the system SHALL return an empty list

#### Scenario: Unauthorized user cannot view join requests

- **WHEN** a user who does not satisfy `can_manage_class` for class C sends `GET /classes/{class_id}/join-requests`
- **THEN** the system MUST return HTTP 403


<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->

---
### Requirement: Teacher reviews join request

Teachers SHALL be able to approve or reject pending join requests for their managed class. The `review_join_request()` service function SHALL accept a `class_id` parameter and SHALL verify that the loaded JoinRequest belongs to the specified class. If `jr.class_id != class_id`, the function SHALL raise a ValueError. When approving, the function SHALL check for an existing ClassMembership before inserting — if a membership already exists for that (class_id, user_id) pair, the insert SHALL be skipped (idempotent approval).

#### Scenario: Teacher approves join request for own class

- **WHEN** a teacher who manages class C approves a join request belonging to class C
- **THEN** the system SHALL mark the request as approved and create a ClassMembership if none exists

#### Scenario: Teacher attempts to review join request from another class

- **WHEN** a teacher who manages class A attempts to review a join request belonging to class B
- **THEN** the system SHALL raise a ValueError indicating the request does not belong to the specified class

#### Scenario: Idempotent approval when membership already exists

- **WHEN** a teacher approves a join request for a student who already has a ClassMembership in that class
- **THEN** the system SHALL mark the request as approved but SHALL NOT create a duplicate ClassMembership


<!-- @trace
source: fix-codex-review-findings
updated: 2026-04-03
code:
  - .agents/workflows
  - .agents/skills/spectra-discuss
  - .agents/workflows/spectra-ingest.md
  - .github/skills/spectra-ask/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-002.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-004.md
  - .github/prompts/spectra-debug.prompt.md
  - .github/prompts/spectra-propose.prompt.md
  - .github/skills/spectra-archive/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-005.md
  - .security-audit/active/dprs-full-review-2026-04-02/scope.md
  - .agents/skills/spectra-propose/SKILL.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/workflows/spectra-ask.md
  - .github/skills/spectra-audit/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/.audit.yaml
  - .agents/workflows/spectra-archive.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-003.md
  - .agents/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-ingest
  - .agents/workflows/spectra-apply.md
  - .github/skills/spectra-apply/SKILL.md
  - .github/skills/spectra-propose/SKILL.md
  - AGENTS.md
  - .agents/workflows/spectra-propose.md
  - .agents/skills/spectra-archive/SKILL.md
  - .github/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - .agents/skills/spectra-audit
  - .security-audit/active/dprs-full-review-2026-04-02/tasks.md
  - .github/prompts/spectra-archive.prompt.md
  - .agents/skills/spectra-debug
  - GEMINI.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-001.md
  - .agents/skills/spectra-audit/SKILL.md
  - .github/prompts/spectra-apply.prompt.md
  - .github/skills/spectra-ingest/SKILL.md
  - .github/prompts/spectra-ask.prompt.md
  - .github/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply
  - .agents/skills
  - .agents/skills/spectra-propose
  - .github/prompts/spectra-discuss.prompt.md
  - .github/prompts/spectra-ingest.prompt.md
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-archive
  - .agents/skills/spectra-ask
  - .github/prompts/spectra-audit.prompt.md
  - .security-audit/active/dprs-full-review-2026-04-02/plan.md
  - .agents/workflows/spectra-debug.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .codex/environments/environment.toml
  - .agents/workflows/spectra-audit.md
  - .agents/workflows/spectra-discuss.md
-->

---
### Requirement: Student join request UI

The student dashboard SHALL display a "Join Class" button. When clicked, a modal dialog SHALL appear containing a single text input field for the invite code and a submit button. On successful submission, the modal SHALL display a confirmation message indicating the request is pending teacher review. On failure, the modal SHALL display the appropriate error message.

#### Scenario: Student opens join class modal

- **WHEN** a student clicks the "Join Class" button on the dashboard
- **THEN** a modal dialog SHALL appear with an invite code input field and a submit button

#### Scenario: Successful submission feedback

- **WHEN** a student submits a valid invite code and the join request is created successfully
- **THEN** the modal SHALL display a message confirming the request is pending review

#### Scenario: Error feedback on submission failure

- **WHEN** a student submits an invite code and the server returns an error (invalid code, duplicate request, cooldown, etc.)
- **THEN** the modal SHALL display the error message returned by the server


<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->

---
### Requirement: Teacher pending review UI section

The class members page (`class_members.html`) SHALL display a "Pending Review" section above the existing member list. This section SHALL list all pending `JoinRequest` records for the class, showing student name, request time, and invite code used. Each entry SHALL have an "Approve" button and a "Reject" button. When no pending requests exist, the section SHALL display an empty state message.

#### Scenario: Pending requests displayed

- **WHEN** a teacher views the class members page and there are pending join requests
- **THEN** the page SHALL display each pending request with student information and approve/reject buttons

#### Scenario: Approve action from UI

- **WHEN** a teacher clicks the "Approve" button for a pending request
- **THEN** the UI SHALL call `PATCH /classes/{class_id}/join-requests/{id}/review` with `action = "approve"` and update the display to reflect the change

#### Scenario: Reject action from UI

- **WHEN** a teacher clicks the "Reject" button for a pending request
- **THEN** the UI SHALL call `PATCH /classes/{class_id}/join-requests/{id}/review` with `action = "reject"` and update the display to reflect the change

#### Scenario: Empty state when no pending requests

- **WHEN** a teacher views the class members page and there are no pending join requests
- **THEN** the pending review section SHALL display a message indicating there are no pending requests

<!-- @trace
source: invite-code-join-review
updated: 2026-03-25
code:
  - scripts/migrations/20260325_004_join_request_index.py
  - src/main.py
  - src/shared/page_context.py
  - uv.lock
  - src/pages/router.py
  - src/templates/teacher/class_members.html
  - src/core/classes/router.py
  - src/core/classes/service.py
  - src/templates/student/dashboard.html
  - src/core/classes/models.py
  - src/core/system/router.py
  - src/core/system/models.py
  - src/templates/admin/system_settings.html
tests:
  - tests/test_join_requests.py
-->