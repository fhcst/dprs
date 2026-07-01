## ADDED Requirements

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
