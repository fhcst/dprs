## ADDED Requirements

### Requirement: Password strength indicator

The password change form SHALL display a real-time strength indicator as the user types a new password. The indicator SHALL classify strength into three levels: weak (red), medium (amber), strong (green) based on password length and character variety.

#### Scenario: User types a weak password

- **WHEN** a user types a password shorter than 8 characters in the new password field
- **THEN** the strength indicator SHALL display "弱" with red styling

#### Scenario: User types a strong password

- **WHEN** a user types a password of 10+ characters containing uppercase, lowercase, numbers, and symbols
- **THEN** the strength indicator SHALL display "強" with green styling

### Requirement: Date range cross-field validation

The template assignment form SHALL validate that the start date is not after the end date. When the validation fails, both date fields SHALL display a red border and an error message SHALL appear below the fields.

#### Scenario: Start date is after end date

- **WHEN** a teacher sets a start date of 2026-04-15 and an end date of 2026-04-10
- **THEN** both date inputs SHALL display a red border
- **THEN** an error message "起始日期不可晚於結束日期" SHALL appear below the date fields

#### Scenario: Valid date range is entered

- **WHEN** a teacher sets a start date of 2026-04-10 and an end date of 2026-04-15
- **THEN** both date inputs SHALL have their normal border styling
- **THEN** no error message SHALL be displayed

### Requirement: Invite code format feedback

The invite code input in the join class modal SHALL auto-transform input to uppercase and limit the maximum length to 8 characters.

#### Scenario: User types lowercase invite code

- **WHEN** a user types "abc123" in the invite code input
- **THEN** the displayed value SHALL be "ABC123"

#### Scenario: User types more than 8 characters

- **WHEN** a user attempts to type more than 8 characters in the invite code input
- **THEN** the input SHALL NOT accept characters beyond the 8th

### Requirement: Username uniqueness check

The admin user creation form SHALL perform a debounced uniqueness check when the username field loses focus. If the username already exists, an error message SHALL appear below the field.

#### Scenario: Admin enters an existing username

- **WHEN** an admin types an existing username and the field loses focus
- **THEN** an error message "此帳號已存在" SHALL appear below the username field
- **THEN** the field border SHALL turn red

#### Scenario: Admin enters a new unique username

- **WHEN** an admin types a username that does not exist and the field loses focus
- **THEN** no error message SHALL appear
- **THEN** the field SHALL display a green checkmark indicator
