## ADDED Requirements

### Requirement: Template modification requires class management permission

The system SHALL verify that the requesting user can manage the class a template belongs to before allowing update, delete, archive, or unarchive operations. The system SHALL load the template, retrieve its `class_id`, load the corresponding Class document, and call `can_manage_class(user, cls)`. If the user cannot manage the class, the system SHALL return HTTP 403.

#### Scenario: Teacher modifies template in own class

- **WHEN** a teacher with `MANAGE_TASKS` permission and teacher membership in class C calls `PATCH /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL proceed with the update normally

#### Scenario: Teacher modifies template in another class

- **WHEN** a teacher with `MANAGE_TASKS` permission but no membership in class C calls `PATCH /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL return HTTP 403

#### Scenario: Class manager modifies any template

- **WHEN** a user with `MANAGE_ALL_CLASSES` permission calls `PATCH /templates/{template_id}` for any template
- **THEN** the system SHALL proceed with the update normally

#### Scenario: Teacher deletes template in another class

- **WHEN** a teacher with `MANAGE_TASKS` permission but no membership in class C calls `DELETE /templates/{template_id}` for a template belonging to class C
- **THEN** the system SHALL return HTTP 403
