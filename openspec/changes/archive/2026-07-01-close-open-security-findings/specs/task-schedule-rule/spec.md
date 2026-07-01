## ADDED Requirements

### Requirement: Schedule rule request validation

The schedule-rule creation endpoint (`POST /classes/{class_id}/schedule-rules`) SHALL validate the request body before persisting anything. `schedule_type` SHALL be constrained to one of `once`, `range`, or `open`. The system SHALL enforce the mode-specific required date fields — `once` requires `date`; `range` requires `start_date` and `end_date` with `end_date` on or after `start_date`; `open` requires `start_date` — and `weekdays` entries SHALL be within 0–6. A request that fails validation SHALL be rejected with HTTP 422 and SHALL NOT create a `TaskScheduleRule` or any `TaskAssignment`.

#### Scenario: Malformed rule is rejected before persistence

- **WHEN** a schedule-rule request omits a field required by its `schedule_type` (e.g. `once` without `date`, or `range` without `end_date`), or uses an unknown `schedule_type`
- **THEN** the system SHALL return HTTP 422 and SHALL NOT persist a `TaskScheduleRule` or any `TaskAssignment`

#### Scenario: Valid rule is created

- **WHEN** a well-formed schedule-rule request is submitted by a teacher who manages the class
- **THEN** the system SHALL create the `TaskScheduleRule` and expand it into the corresponding `TaskAssignment` records
