## ADDED Requirements

### Requirement: Teacher template pages enforce class management

The teacher template pages SHALL enforce class-management authorization on the class derived from the URL. Class-scoped pages (`templates_list_page`, `template_form_page` under `/pages/teacher/classes/{class_id}/templates...`) SHALL require `can_manage_class()` on `class_id`; template-scoped pages (`template_edit_page`, `template_assign_page` under `/pages/teacher/templates/{template_id}/...`) SHALL resolve the template's class and require `can_manage_class()` on it. A teacher who does not manage the class SHALL receive HTTP 403 before any template definition, invite code, or Discord-webhook metadata is disclosed.

#### Scenario: Non-managing teacher lists another class's templates

- **WHEN** a teacher who does not manage the class requests its templates list page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose template definitions

#### Scenario: Non-managing teacher opens a template edit or assign page

- **WHEN** a teacher requests the edit or assign page for a template whose class they do not manage
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose the template or its class's Discord-webhook presence

#### Scenario: Managing teacher opens their own template pages

- **WHEN** a teacher who manages the class requests any of these pages
- **THEN** the system SHALL render the page normally
