## MODIFIED Requirements

### Requirement: Student joins a class

Students SHALL be able to join a class using a class invite code or by browsing public classes. A student MUST be able to join multiple classes simultaneously. When joining via invite code, the system SHALL create a `JoinRequest` with status `pending` instead of directly creating a `ClassMembership`. The student SHALL be informed that their request is pending teacher review. Joining a public class SHALL continue to add the student as a member directly without requiring review.

#### Scenario: Student submits invite code to request joining

- **WHEN** a student submits a valid invite code
- **THEN** the system SHALL create a `JoinRequest` with status `pending` for the corresponding class and return a message indicating the request is awaiting teacher review

#### Scenario: Student joins a public class

- **WHEN** a student selects a public class from the class browser
- **THEN** the system SHALL add the student as a member directly (no review required)

#### Scenario: Student already a member

- **WHEN** a student attempts to join a class they already belong to
- **THEN** the system SHALL return an informational message and SHALL NOT create a duplicate membership or join request
