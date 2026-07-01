## ADDED Requirements

### Requirement: Points operations require class management permission

The system SHALL verify that the requesting user can manage the class before allowing point deduction, revocation, or configuration changes. For `POST /api/points/deduct`, the system SHALL verify the teacher can manage the class specified in `body.class_id`. For `POST /classes/{class_id}/students/{student_id}/point-revoke` and `PATCH /classes/{class_id}/point-config`, the system SHALL verify the teacher can manage the class from the URL path. If verification fails, the system SHALL return HTTP 403.

#### Scenario: Teacher deducts points in own class

- **WHEN** a teacher with `MANAGE_TASKS` permission and teacher membership in class C calls `POST /api/points/deduct` with `class_id` referring to class C
- **THEN** the system SHALL proceed with the deduction normally

#### Scenario: Teacher deducts points in another class

- **WHEN** a teacher with `MANAGE_TASKS` permission but no membership in class C calls `POST /api/points/deduct` with `class_id` referring to class C
- **THEN** the system SHALL return HTTP 403
