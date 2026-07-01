## MODIFIED Requirements

### Requirement: Teacher batch-invites students to a class

A user authorized to manage a class SHALL be able to browse all students not yet in that class via an enumerate-first interface and directly add multiple students in a single operation. The UI MUST display all available students grouped by category (grade/class or tags) with category select-all and client-side search filtering. The existing search API (`GET /classes/{class_id}/invite/search`) SHALL remain available for backward compatibility. Invited students SHALL be added immediately as members with role `student` without requiring student confirmation.

#### Scenario: Teacher views all available students on page load

- **WHEN** an authorized teacher navigates to the class member management page
- **THEN** the invite panel SHALL begin loading all non-member students via paginated API and display them grouped by grade and administrative class

#### Scenario: Teacher searches students by administrative class name

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/search?q=302&type=class_name`
- **THEN** the system SHALL return a list of users with `STUDENT` identity tag whose `student_profile.class_name` contains `"302"` and who are NOT already members of class `{class_id}`

#### Scenario: Teacher searches students by name

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/search?q=陳&type=name`
- **THEN** the system SHALL return a list of users with `STUDENT` identity tag whose `name` contains `"陳"` and who are NOT already members of class `{class_id}`

#### Scenario: Teacher batch-adds students

- **WHEN** an authorized teacher sends `POST /classes/{class_id}/invite/batch` with a list of user IDs
- **THEN** all specified users SHALL be added as members of class `{class_id}` with role `student`, and users already in the class MUST be silently skipped

#### Scenario: Unauthorized user cannot batch-invite

- **WHEN** a user who does not satisfy `can_manage_class` for the given class sends `POST /classes/{class_id}/invite/batch`
- **THEN** the system MUST return HTTP 403
