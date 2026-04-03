## MODIFIED Requirements

### Requirement: Student joins a class

The system SHALL NOT create duplicate ClassMembership records. Before inserting a new ClassMembership, the service layer SHALL check if a membership already exists for the given (class_id, user_id) pair. If a membership already exists, the insert SHALL be skipped silently. This applies to all membership creation paths: join-request approval, batch invite, and direct join.

#### Scenario: Approval does not duplicate existing membership

- **WHEN** a join request is approved for a student who already has a ClassMembership in that class
- **THEN** the system SHALL NOT insert a second ClassMembership record

#### Scenario: First-time approval creates membership

- **WHEN** a join request is approved for a student who has no existing ClassMembership in that class
- **THEN** the system SHALL insert a new ClassMembership record with role "student"
