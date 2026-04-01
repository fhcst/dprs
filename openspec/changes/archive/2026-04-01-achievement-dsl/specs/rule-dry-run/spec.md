## ADDED Requirements

### Requirement: Student stats aggregation API

The system SHALL provide an endpoint `GET /api/classes/{class_id}/students/stats` that returns aggregated statistics for all students in the class. Each student entry MUST include: `student_id`, `name`, `checkin_count`, `checkin_streak`, `submission_count`, `points`, `badge_count`. The endpoint SHALL accept an optional `windows` query parameter (comma-separated integers) to include time-window pre-computed values (e.g., `windows=7,30` adds `submissions_last_7_days`, `checkins_last_7_days`, `submissions_last_30_days`, `checkins_last_30_days`). The endpoint SHALL require `MANAGE_OWN_CLASS` permission and pass `can_manage_class()` CBAC verification.

#### Scenario: Teacher fetches class student stats

- **WHEN** a teacher who manages class C calls `GET /api/classes/{class_id}/students/stats`
- **THEN** the system SHALL return a JSON array with aggregated stats for all students in class C

#### Scenario: Teacher fetches stats with time windows

- **WHEN** a teacher calls `GET /api/classes/{class_id}/students/stats?windows=7`
- **THEN** the system SHALL include `submissions_last_7_days` and `checkins_last_7_days` fields for each student

#### Scenario: Non-manager blocked from stats access

- **WHEN** a user without class management permission calls `GET /api/classes/{class_id}/students/stats`
- **THEN** the system SHALL return HTTP 403

### Requirement: Frontend dry-run test execution

The trigger rule management page SHALL provide a "Test Rule" button. When pressed, the system SHALL fetch student stats from the stats API, then use the WASM `evaluate()` function to test the current expression against each student's data in the browser. The results SHALL be displayed as a table showing each student's name, relevant variable values, and pass/fail status. Students who already hold a badge bound to this rule SHALL be marked with a visual indicator noting they will not receive a duplicate award.

#### Scenario: Dry-run shows matching students

- **WHEN** a teacher clicks "Test Rule" with expression `checkin_streak >= 7` and 3 of 25 students meet the condition
- **THEN** the page SHALL display a results table showing 3 students as matching and 22 as not matching, with each student's `checkin_streak` value visible

#### Scenario: Dry-run marks existing badge holders

- **WHEN** the dry-run results include a student who already holds a badge bound to this rule
- **THEN** that student's row SHALL display a visual indicator stating the badge will not be re-awarded

#### Scenario: Dry-run with invalid expression

- **WHEN** a teacher clicks "Test Rule" with an expression that has validation errors
- **THEN** the system SHALL display the validation errors instead of running the test
