## ADDED Requirements

### Requirement: Password hashing uses Argon2id

The system SHALL hash all passwords using the Argon2id algorithm via the argon2-cffi library. The system SHALL use the library's default parameters, which conform to OWASP recommendations. The system SHALL NOT use bcrypt, passlib, or any other password hashing library.

#### Scenario: New password is hashed with Argon2id

- **WHEN** a user account is created or a password is changed
- **THEN** the stored `hashed_password` SHALL be an Argon2id hash (prefixed with `$argon2id$`)

#### Scenario: Password verification uses Argon2id

- **WHEN** a user attempts to log in with a valid password
- **THEN** the system SHALL verify the password against the Argon2id hash and grant access

#### Scenario: Timing-safe dummy verification for unknown users

- **WHEN** a login attempt is made with a username that does not exist
- **THEN** the system SHALL perform a dummy Argon2id verification to prevent timing side-channel attacks (CWE-208)
- **AND** the dummy hash SHALL be in Argon2id format to ensure consistent timing with real verifications
