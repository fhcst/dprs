## ADDED Requirements

### Requirement: Prize listing enforces class-scoped authorization

The prize listing endpoint `GET /classes/{class_id}/prizes` SHALL enforce class-scoped authorization. It SHALL load the class and return HTTP 404 if it does not exist. A caller who manages the class (`can_manage_class`) SHALL receive all prizes; a caller who is a member of the class SHALL receive only prizes with `visible == true`; a caller who is neither SHALL receive HTTP 403 and no prize data.

#### Scenario: Non-member enumerates another class's prizes

- **WHEN** an authenticated user who is not a member of the class and does not manage it requests the class's prize listing
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose any prize

#### Scenario: Member sees only visible prizes

- **WHEN** a class member who does not manage the class requests the prize listing
- **THEN** the system SHALL return only prizes with `visible == true`

#### Scenario: Manager sees all prizes

- **WHEN** a teacher who manages the class requests the prize listing
- **THEN** the system SHALL return all prizes, including those with `visible == false`
