## MODIFIED Requirements

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

### Requirement: Teacher rejects a task submission

Teachers with `MANAGE_TASKS` permission SHALL be able to reject a `TaskSubmission` by calling `POST /api/submissions/{submission_id}/reject` with a required `rejection_reason` (string) and optional `resubmit_deadline` (ISO 8601 datetime, nullable). The system SHALL verify that the teacher can manage the class the submission belongs to before proceeding. If the teacher cannot manage the class, the system SHALL return HTTP 403. Rejection SHALL set `status` to `"rejected"`, store the reason and deadline, and create a negative `PointTransaction` equal to the class `submission_points` (source_event: `"submission_rejected"`).

#### Scenario: Teacher rejects a submission with reason

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/reject` with a valid `rejection_reason` for a submission in a class they manage
- **THEN** the system SHALL set `status` to `"rejected"`, store `rejection_reason` and `resubmit_deadline`
- **AND** the system SHALL create a negative `PointTransaction` equal to `submission_points`

#### Scenario: Rejection without reason is rejected

- **WHEN** a teacher calls `POST /api/submissions/{submission_id}/reject` with an empty `rejection_reason`
- **THEN** the system SHALL return HTTP 422 and SHALL NOT change the submission status

#### Scenario: Teacher rejects submission in another class

- **WHEN** a teacher with `MANAGE_TASKS` but no membership in class C calls `POST /api/submissions/{submission_id}/reject` for a submission in class C
- **THEN** the system SHALL return HTTP 403
