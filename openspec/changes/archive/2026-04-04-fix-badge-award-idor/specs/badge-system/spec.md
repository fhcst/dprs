## MODIFIED Requirements

### Requirement: Teacher awards badge manually

Teachers SHALL be able to manually award any defined badge to a student in their class, with an optional reason note. The system SHALL verify that the target student is a member of the class with the `"student"` role before awarding the badge. If the target user is not a student member of the class, the system SHALL reject the request with HTTP 403.

#### Scenario: Teacher manually awards badge to class student

- **WHEN** a teacher submits a manual badge award with a `student_id` that is a student member of the class
- **THEN** the system SHALL create a badge award record with manual award source

#### Scenario: Teacher attempts to award badge to non-member

- **WHEN** a teacher submits a manual badge award with a `student_id` that has no ClassMembership in the class
- **THEN** the system SHALL reject the request with HTTP 403 and detail "Student is not a member of this class"

#### Scenario: Teacher attempts to award badge to non-student member

- **WHEN** a teacher submits a manual badge award with a `student_id` that is a member of the class but with role `"teacher"` (not `"student"`)
- **THEN** the system SHALL reject the request with HTTP 403 and detail "Student is not a member of this class"
