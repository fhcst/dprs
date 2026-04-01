## MODIFIED Requirements

### Requirement: Teacher reviews join request

Teachers SHALL be able to approve or reject pending join requests for their managed class. The `review_join_request()` service function SHALL accept a `class_id` parameter and SHALL verify that the loaded JoinRequest belongs to the specified class. If `jr.class_id != class_id`, the function SHALL raise a ValueError. When approving, the function SHALL check for an existing ClassMembership before inserting — if a membership already exists for that (class_id, user_id) pair, the insert SHALL be skipped (idempotent approval).

#### Scenario: Teacher approves join request for own class

- **WHEN** a teacher who manages class C approves a join request belonging to class C
- **THEN** the system SHALL mark the request as approved and create a ClassMembership if none exists

#### Scenario: Teacher attempts to review join request from another class

- **WHEN** a teacher who manages class A attempts to review a join request belonging to class B
- **THEN** the system SHALL raise a ValueError indicating the request does not belong to the specified class

#### Scenario: Idempotent approval when membership already exists

- **WHEN** a teacher approves a join request for a student who already has a ClassMembership in that class
- **THEN** the system SHALL mark the request as approved but SHALL NOT create a duplicate ClassMembership
