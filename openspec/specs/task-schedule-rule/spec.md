# task-schedule-rule Specification

## Purpose

Defines the TaskScheduleRule system for assigning task templates to dates using flexible scheduling modes: one-time, date-range (with or without weekday filter), and open-ended.

## Requirements

### Requirement: Teacher creates a one-time task schedule

A teacher SHALL be able to assign a task template to a single specific date using a one-time schedule. The system SHALL create exactly one `TaskAssignment` record for that date when the schedule rule is saved.

#### Scenario: One-time schedule creates single assignment

- **WHEN** a teacher saves a schedule rule with `schedule_type: "once"` and a specific `date`
- **THEN** exactly one `TaskAssignment` record is created for that `(template_id, class_id, date)` combination
- **AND** the rule is persisted as a `TaskScheduleRule` document

---
### Requirement: Teacher creates a date-range task schedule

A teacher SHALL be able to assign a task template to every day within a date range. An optional weekday filter (list of integers 0–6) SHALL restrict assignments to only matching days of the week. If the weekday filter is empty, all days in the range are included. The system SHALL batch-create `TaskAssignment` records for all qualifying dates when the rule is saved.

#### Scenario: Range schedule with no weekday filter

- **WHEN** a teacher saves a schedule rule with `schedule_type: "range"`, `start_date`, `end_date`, and `weekdays: []`
- **THEN** one `TaskAssignment` is created for every calendar day in the range (inclusive)

#### Scenario: Range schedule with weekday filter

- **WHEN** a teacher saves a schedule rule with `schedule_type: "range"`, `start_date`, `end_date`, and `weekdays: [0, 1, 3, 4]`
- **THEN** `TaskAssignment` records are created only for dates within the range whose weekday is Monday, Tuesday, Thursday, or Friday

---
### Requirement: Teacher creates an open-ended task schedule

A teacher SHALL be able to assign a task template starting from a given date with no fixed end date. The system SHALL expand this into `TaskAssignment` records for at most 90 future days from the start date.

#### Scenario: Open schedule expands up to 90 days

- **WHEN** a teacher saves a schedule rule with `schedule_type: "open"` and a `start_date`
- **THEN** `TaskAssignment` records are created for every day from `start_date` up to `start_date + 89 days` (90 days total)
- **AND** `end_date` is stored as `None` on the rule

---
### Requirement: Teacher sets a per-student submission limit on a schedule rule

A teacher SHALL be able to set a maximum number of task submissions allowed per student for a given schedule rule. When `max_submissions_per_student` is 0, no limit is enforced. When greater than 0, the submission endpoint SHALL reject submissions that exceed the limit.

#### Scenario: Submission rejected when limit reached

- **WHEN** a student attempts to submit a task and their submission count for the template's schedule rule equals `max_submissions_per_student`
- **THEN** the submission endpoint returns HTTP 409
- **AND** the rejection reason indicates the submission limit has been reached

#### Scenario: No limit when max_submissions_per_student is zero

- **WHEN** `max_submissions_per_student` is `0` for a schedule rule
- **THEN** students MAY submit as many times as there are open dates without restriction

<!-- @trace
source: task-scheduling-and-checkin
updated: 2026-03-19
-->

---
### Requirement: Schedule rule request validation

The schedule-rule creation endpoint (`POST /classes/{class_id}/schedule-rules`) SHALL validate the request body before persisting anything. `schedule_type` SHALL be constrained to one of `once`, `range`, or `open`. The system SHALL enforce the mode-specific required date fields — `once` requires `date`; `range` requires `start_date` and `end_date` with `end_date` on or after `start_date`; `open` requires `start_date` — and `weekdays` entries SHALL be within 0–6. A request that fails validation SHALL be rejected with HTTP 422 and SHALL NOT create a `TaskScheduleRule` or any `TaskAssignment`.

#### Scenario: Malformed rule is rejected before persistence

- **WHEN** a schedule-rule request omits a field required by its `schedule_type` (e.g. `once` without `date`, or `range` without `end_date`), or uses an unknown `schedule_type`
- **THEN** the system SHALL return HTTP 422 and SHALL NOT persist a `TaskScheduleRule` or any `TaskAssignment`

#### Scenario: Valid rule is created

- **WHEN** a well-formed schedule-rule request is submitted by a teacher who manages the class
- **THEN** the system SHALL create the `TaskScheduleRule` and expand it into the corresponding `TaskAssignment` records
