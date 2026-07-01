## ADDED Requirements

### Requirement: Badge detail modal displays awarded and not-awarded students

The badge management page SHALL make each badge card clickable. When a teacher clicks a badge card, the system SHALL fetch badge detail data via `GET /classes/{class_id}/badges/{badge_id}/detail` and display a modal with:
- Badge metadata (name, icon, description, trigger type label)
- An "awarded" section listing students who currently hold the badge, each showing student name, awarded date, and a "收回" (revoke) button
- A "not awarded" section listing students who do not currently hold the badge

The student lists SHALL be sourced from `ClassMembership` records with `role == "student"` for the given class. The modal SHALL NOT display students from other classes.

#### Scenario: Teacher clicks badge card to open detail modal

- **WHEN** a teacher clicks a badge card on the badge management page
- **THEN** the system SHALL fetch the badge detail API and display a modal showing awarded and not-awarded student lists

#### Scenario: Detail modal shows correct counts

- **WHEN** the detail modal is displayed for a badge with 3 awarded students in a class of 25 students
- **THEN** the awarded section SHALL show 3 students and the not-awarded section SHALL show 22 students

### Requirement: Manual badge award from detail modal

For badges with no trigger source (manual badges), the detail modal SHALL display a "頒發" (award) button next to each student in the "not awarded" section. When the teacher clicks "頒發", the system SHALL call `POST /classes/{class_id}/badges/{badge_id}/award` with the student's ID and refresh the modal content without reloading the page. After a successful award, the student SHALL move from "not awarded" to "awarded" in the modal, and the badge card's award count SHALL update.

For badges with a `trigger_key` or `trigger_rule_id`, the "頒發" button SHALL NOT be displayed in the "not awarded" section.

#### Scenario: Teacher awards manual badge from modal

- **WHEN** a teacher clicks "頒發" next to a student in the not-awarded list for a manual badge
- **THEN** the system SHALL award the badge to that student and update the modal in-place to reflect the change

#### Scenario: Award button hidden for automatic trigger badges

- **WHEN** a teacher opens the detail modal for a badge with a `trigger_key` or `trigger_rule_id`
- **THEN** the "not awarded" section SHALL NOT display "頒發" buttons

### Requirement: Badge revoke from detail modal

The detail modal SHALL display a "收回" (revoke) button next to each student in the "awarded" section, regardless of badge trigger type. When the teacher clicks "收回", the system SHALL call `POST /classes/{class_id}/badges/{badge_id}/revoke` with the award ID. After a successful revoke, the student SHALL move from "awarded" to "not awarded" in the modal, and the badge card's award count SHALL update.

#### Scenario: Teacher revokes a badge from modal

- **WHEN** a teacher clicks "收回" next to an awarded student
- **THEN** the system SHALL soft-delete the badge award and update the modal in-place to reflect the change

#### Scenario: Revoke works for all badge types

- **WHEN** a teacher opens the detail modal for a badge with a `trigger_rule_id` and clicks "收回" on an awarded student
- **THEN** the system SHALL revoke the badge award successfully

### Requirement: Badge detail API

The system SHALL provide `GET /classes/{class_id}/badges/{badge_id}/detail` requiring `MANAGE_TASKS` permission. The endpoint SHALL return:
- Badge metadata (`id`, `name`, `icon`, `description`, `trigger_key`, `trigger_rule_id`)
- `is_manual`: boolean, true when both `trigger_key` and `trigger_rule_id` are null
- `awarded`: array of objects with `award_id`, `student_id`, `student_name`, `awarded_at`, `awarded_by`, `reason` — only active awards (`revoked_at` is null)
- `not_awarded`: array of objects with `student_id`, `student_name`

The endpoint SHALL verify `can_manage_class(user, cls)` and `badge.class_id == class_id`. Student lists SHALL be derived from `ClassMembership(class_id, role="student")`.

#### Scenario: Teacher fetches badge detail for own class

- **WHEN** a teacher who manages class C calls `GET /classes/{C}/badges/{B}/detail` where badge B belongs to class C
- **THEN** the system SHALL return badge metadata with awarded and not-awarded student lists

#### Scenario: Teacher fetches badge detail for another class

- **WHEN** a teacher who does NOT manage class C calls `GET /classes/{C}/badges/{B}/detail`
- **THEN** the system SHALL return HTTP 403

#### Scenario: Badge not found or wrong class

- **WHEN** a teacher calls `GET /classes/{C}/badges/{B}/detail` where badge B does not exist or belongs to a different class
- **THEN** the system SHALL return HTTP 404
