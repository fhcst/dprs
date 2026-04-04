## ADDED Requirements

### Requirement: Badge award soft delete with revoke

The `BadgeAward` model SHALL include two optional fields: `revoked_at` (datetime, default null) and `revoked_by` (string, default null). An award with `revoked_at` set to a non-null value SHALL be considered revoked. All queries that count or list badge awards SHALL exclude revoked awards (filter by `revoked_at == None`) unless explicitly querying revocation history.

#### Scenario: Active award has null revoked fields

- **WHEN** a badge is awarded to a student
- **THEN** the `BadgeAward` record SHALL have `revoked_at == None` and `revoked_by == None`

#### Scenario: Revoked award is excluded from counts

- **WHEN** a badge award has been revoked (`revoked_at` is not null)
- **THEN** queries for active badge counts (dashboard, leaderboard, trigger evaluation, management page) SHALL NOT include this award

### Requirement: Teacher revokes badge award

The system SHALL provide `POST /classes/{class_id}/badges/{badge_id}/revoke` requiring `MANAGE_TASKS` permission. The request body SHALL contain `award_id` (string). The endpoint SHALL perform a soft delete by setting `revoked_at` to the current UTC timestamp and `revoked_by` to the teacher's user ID.

The endpoint SHALL verify:
1. `can_manage_class(teacher, cls)` — teacher manages this class
2. `badge.class_id == class_id` — badge belongs to this class
3. `award.badge_id == badge_id` and `award.class_id == class_id` — award belongs to this badge and class
4. `award.revoked_at is None` — award has not already been revoked

If any verification fails, the system SHALL return the appropriate HTTP error (403 for permission, 404 for not found, 409 for already revoked).

#### Scenario: Teacher revokes an active badge award

- **WHEN** a teacher who manages class C calls `POST /classes/{C}/badges/{B}/revoke` with a valid `award_id` for an active award
- **THEN** the system SHALL set `revoked_at` to the current UTC timestamp and `revoked_by` to the teacher's user ID, and return HTTP 200

#### Scenario: Teacher attempts to revoke award from another class

- **WHEN** a teacher calls `POST /classes/{C}/badges/{B}/revoke` with an `award_id` belonging to a different class
- **THEN** the system SHALL return HTTP 404

#### Scenario: Teacher attempts to revoke already-revoked award

- **WHEN** a teacher calls `POST /classes/{C}/badges/{B}/revoke` with an `award_id` that has `revoked_at` set
- **THEN** the system SHALL return HTTP 409 with detail "Award already revoked"

#### Scenario: Non-managing teacher attempts to revoke

- **WHEN** a teacher who does NOT manage class C calls `POST /classes/{C}/badges/{B}/revoke`
- **THEN** the system SHALL return HTTP 403

### Requirement: Re-awarding a previously revoked badge

When checking for duplicate awards in `award_badge()`, the system SHALL only consider active awards (`revoked_at == None`). A student whose badge was previously revoked SHALL be eligible to receive the same badge again, creating a new `BadgeAward` record. The revoked award record SHALL remain in the database as audit history.

#### Scenario: Student receives badge after previous revocation

- **WHEN** a student's badge award was revoked and the teacher awards the same badge again
- **THEN** the system SHALL create a new `BadgeAward` record and the database SHALL contain both the revoked and the new active award

#### Scenario: Student with active award cannot receive duplicate

- **WHEN** a student already holds an active (non-revoked) award for a badge and the teacher attempts to award it again
- **THEN** the system SHALL return HTTP 409 with detail "Student already holds this badge"

## MODIFIED Requirements

### Requirement: Student views earned badges

Students SHALL be able to view all badges they have earned, including badge name, icon, description, and date awarded. The badge list SHALL only include active awards (`revoked_at` is null). Revoked badges SHALL NOT appear in the student's badge collection.

#### Scenario: Student views badge collection

- **WHEN** a student navigates to their profile or badge page
- **THEN** the system SHALL display all active (non-revoked) earned badges with award dates

#### Scenario: Revoked badge not shown to student

- **WHEN** a student's badge has been revoked by a teacher
- **THEN** the badge SHALL NOT appear in the student's badge collection
