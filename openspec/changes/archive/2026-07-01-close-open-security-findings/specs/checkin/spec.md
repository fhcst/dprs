## ADDED Requirements

### Requirement: Attendance page enforces class management

The teacher attendance page `GET /pages/teacher/classes/{class_id}/attendance` SHALL verify the caller manages the requested class via `can_manage_class()`, not merely that the caller holds a class-management permission flag. A teacher who does not manage the class SHALL receive HTTP 403 before the roster or attendance data is loaded or rendered.

#### Scenario: Non-managing teacher opens another class's attendance page

- **WHEN** a teacher who does not manage the class requests its attendance page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose the roster or attendance state

#### Scenario: Managing teacher opens their own attendance page

- **WHEN** a teacher who manages the class requests its attendance page
- **THEN** the system SHALL load and render the attendance roster
