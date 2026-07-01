## ADDED Requirements

### Requirement: Badge operations require class management permission

The system SHALL verify that the requesting user can manage the class before allowing badge creation or manual award. For `POST /classes/{class_id}/badges` and `POST /classes/{class_id}/badges/{badge_id}/award`, the system SHALL call `can_manage_class(user, cls)`. If verification fails, the system SHALL return HTTP 403.

#### Scenario: Teacher creates badge in own class

- **WHEN** a teacher who manages class C calls `POST /classes/{class_id}/badges`
- **THEN** the system SHALL proceed normally

#### Scenario: Teacher creates badge in another class

- **WHEN** a teacher who does NOT manage class C calls `POST /classes/{class_id}/badges` for class C
- **THEN** the system SHALL return HTTP 403
