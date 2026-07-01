## ADDED Requirements

### Requirement: Class leaderboard requires membership

The system SHALL verify that the requesting user is a member of the class before returning leaderboard data. For `GET /classes/{class_id}/leaderboard`, the system SHALL check that the user has a `ClassMembership` record for the specified class. If the user is not a member and does not have `MANAGE_ALL_CLASSES` permission, the system SHALL return HTTP 403.

#### Scenario: Class member views leaderboard

- **WHEN** a user who is a member of class C requests `GET /classes/{class_id}/leaderboard`
- **THEN** the system SHALL return the leaderboard data normally

#### Scenario: Non-member views leaderboard

- **WHEN** a user who is NOT a member of class C and lacks `MANAGE_ALL_CLASSES` requests `GET /classes/{class_id}/leaderboard`
- **THEN** the system SHALL return HTTP 403
