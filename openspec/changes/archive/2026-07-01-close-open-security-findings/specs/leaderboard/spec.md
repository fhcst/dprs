## ADDED Requirements

### Requirement: Leaderboard page enforces class membership

The leaderboard HTML page (`GET /pages/classes/{class_id}/leaderboard`) SHALL enforce the same class-membership check as the leaderboard API route. Unless the caller holds `MANAGE_ALL_CLASSES`, the system SHALL require a `ClassMembership` linking the caller to the class; if none exists, the page SHALL return HTTP 403 before computing or rendering any ranking. A class-management permission flag alone SHALL NOT grant access to a class the caller is not a member of.

#### Scenario: Non-member requests the leaderboard page

- **WHEN** an authenticated user who is not a member of the class and lacks `MANAGE_ALL_CLASSES` requests the leaderboard page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT render the ranking

#### Scenario: Member requests the leaderboard page

- **WHEN** a member of the class requests the leaderboard page
- **THEN** the system SHALL proceed to compute the ranking subject to the existing visibility rules

### Requirement: Leaderboard reflects class-scoped points

A class leaderboard SHALL rank students by their point balance within that class only. The ranking SHALL be built from `get_class_balance(student_id, class_id)`, so points a student earned in other classes SHALL NOT appear in this class's ranking.

#### Scenario: Student with points in multiple classes

- **WHEN** a class leaderboard is built for a student who also has points in other classes
- **THEN** the student's displayed points SHALL reflect only the transactions belonging to this class
