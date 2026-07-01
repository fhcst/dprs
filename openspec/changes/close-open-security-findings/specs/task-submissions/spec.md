## ADDED Requirements

### Requirement: Teacher submission routes enforce class management

Every teacher-facing route that returns a class's submission data — the JSON listing endpoint `GET /classes/{class_id}/submissions` and the SSR review page `GET /pages/teacher/class/{class_id}/submissions` — SHALL verify the caller manages the requested class via `can_manage_class()` before returning any data. Holding the `MANAGE_TASKS` permission flag SHALL NOT be sufficient; a teacher who does not manage the class SHALL receive HTTP 403 and no submission data.

#### Scenario: Non-managing teacher lists submissions via the API

- **WHEN** a teacher with `MANAGE_TASKS` requests `GET /classes/{class_id}/submissions` for a class they do not manage
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose any submission data

#### Scenario: Non-managing teacher opens the review page

- **WHEN** a teacher with `MANAGE_TASKS` requests `GET /pages/teacher/class/{class_id}/submissions` for a class they do not manage
- **THEN** the system SHALL return HTTP 403 before rendering, and SHALL NOT disclose the roster or submissions

#### Scenario: Managing teacher reads their own class

- **WHEN** a teacher who manages the class requests either route
- **THEN** the system SHALL return the class's submission data
