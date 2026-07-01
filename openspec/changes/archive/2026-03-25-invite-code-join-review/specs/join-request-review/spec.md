## ADDED Requirements

### Requirement: JoinRequest data model

The system SHALL maintain a `JoinRequest` Beanie Document in the `join_requests` MongoDB collection with the following fields: `class_id` (str), `user_id` (str), `status` (literal: "pending", "approved", "rejected"), `requested_at` (datetime, defaults to UTC now), `reviewed_at` (datetime, nullable), `reviewed_by` (str, nullable), and `invite_code_used` (str). The collection MUST have a partial unique index on `(class_id, user_id)` where `status = "pending"` to ensure only one pending request per student per class.

#### Scenario: Only one pending request per student per class

- **WHEN** a student already has a pending `JoinRequest` for class C and submits another join request for class C
- **THEN** the system MUST reject the request with an error indicating a pending request already exists

#### Scenario: Student can reapply after previous request was resolved

- **WHEN** a student has only approved or rejected `JoinRequest` records for class C (no pending) and the cooldown period has passed
- **THEN** the system SHALL allow the student to create a new `JoinRequest` for class C

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

---

### Requirement: Rate limiting on join request endpoint

The `POST /classes/join-request` endpoint MUST enforce a rate limit of 5 requests per minute per IP address. Requests exceeding the limit MUST be rejected with HTTP 429.

#### Scenario: Requests within rate limit succeed

- **WHEN** a student sends up to 5 join requests within one minute from the same IP
- **THEN** all requests SHALL be processed normally (subject to other validation)

#### Scenario: Requests exceeding rate limit are rejected

- **WHEN** a student sends a 6th join request within one minute from the same IP
- **THEN** the system MUST return HTTP 429

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

---

### Requirement: Teacher reviews join request

An authorized class manager SHALL be able to approve or reject a pending join request via `PATCH /classes/{class_id}/join-requests/{id}/review`. The request body MUST include an `action` field with value `"approve"` or `"reject"`. The endpoint MUST require `can_manage_class` authorization.

#### Scenario: Teacher approves a join request

- **WHEN** an authorized teacher sends a review request with `action = "approve"` for a pending `JoinRequest`
- **THEN** the system SHALL create a `ClassMembership` with role `student` for the requesting user, update the `JoinRequest` status to `"approved"`, set `reviewed_at` to the current UTC time, and set `reviewed_by` to the reviewing teacher's user ID

#### Scenario: Teacher rejects a join request

- **WHEN** an authorized teacher sends a review request with `action = "reject"` for a pending `JoinRequest`
- **THEN** the system SHALL update the `JoinRequest` status to `"rejected"`, set `reviewed_at` to the current UTC time, and set `reviewed_by` to the reviewing teacher's user ID. No `ClassMembership` SHALL be created.

#### Scenario: Review of non-pending request

- **WHEN** a teacher attempts to review a `JoinRequest` that is not in `pending` status
- **THEN** the system MUST return HTTP 400 with a message indicating only pending requests can be reviewed

#### Scenario: Unauthorized user cannot review

- **WHEN** a user who does not satisfy `can_manage_class` for the class sends a review request
- **THEN** the system MUST return HTTP 403

#### Scenario: Join request not found

- **WHEN** a teacher sends a review request with a non-existent join request ID
- **THEN** the system MUST return HTTP 404

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
