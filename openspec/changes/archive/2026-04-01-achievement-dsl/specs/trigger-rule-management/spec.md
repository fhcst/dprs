## ADDED Requirements

### Requirement: TriggerRule data model

The system SHALL store trigger rules in a `triggerrules` MongoDB collection. Each TriggerRule document MUST include: `class_id` (string), `name` (string), `expression` (string containing valid DSL), `is_active` (boolean, default true), `created_by` (string, user_id), `created_at` (datetime), and `updated_at` (datetime). The `expression` field MUST pass DSL validation before persistence.

#### Scenario: TriggerRule created with valid expression

- **WHEN** a teacher submits a trigger rule with name "連續打卡7天" and expression `checkin_streak >= 7`
- **THEN** the system SHALL validate the expression using `dsl_engine.validate()`, persist the document, and return the created rule with its ID

#### Scenario: TriggerRule rejected with invalid expression

- **WHEN** a teacher submits a trigger rule with expression `checkin_streak >= AND 7`
- **THEN** the system SHALL return HTTP 422 with the parse error details from `dsl_engine.validate()`

### Requirement: TriggerRule CRUD API endpoints

The system SHALL provide the following REST endpoints for trigger rule management:
- `POST /api/classes/{class_id}/trigger-rules` — create a new rule
- `GET /api/classes/{class_id}/trigger-rules` — list all rules for the class
- `GET /api/classes/{class_id}/trigger-rules/{rule_id}` — get a single rule
- `PUT /api/classes/{class_id}/trigger-rules/{rule_id}` — update a rule
- `DELETE /api/classes/{class_id}/trigger-rules/{rule_id}` — delete a rule (only if not bound to any badge)

All endpoints SHALL require `MANAGE_OWN_CLASS` permission and pass `can_manage_class()` CBAC verification.

#### Scenario: Teacher creates trigger rule in own class

- **WHEN** a teacher who manages class C calls `POST /api/classes/{class_id}/trigger-rules` with valid data
- **THEN** the system SHALL create the rule and return HTTP 201

#### Scenario: Teacher blocked from managing another class's rules

- **WHEN** a teacher who does NOT manage class C calls `POST /api/classes/{class_id}/trigger-rules` for class C
- **THEN** the system SHALL return HTTP 403

#### Scenario: Delete blocked when rule is bound to badges

- **WHEN** a teacher calls `DELETE /api/classes/{class_id}/trigger-rules/{rule_id}` for a rule that is bound to one or more BadgeDefinitions
- **THEN** the system SHALL return HTTP 409 with a message listing the bound badges

### Requirement: Trigger rule management page

The system SHALL provide an HTML page at `GET /pages/teacher/classes/{class_id}/trigger-rules` for managing trigger rules. The page SHALL display a list of existing rules with name, expression preview, active status, and bound badge count. The page SHALL provide a form to create and edit rules using a CodeMirror 6 editor for the expression field. The page SHALL load the `dsl-engine` WASM module for real-time validation, autocomplete, and hover information within the editor.

#### Scenario: Teacher views trigger rules list

- **WHEN** a teacher navigates to the trigger rules page for their class
- **THEN** the system SHALL display all trigger rules for that class with name, expression, active status, and count of bound badges

#### Scenario: Teacher edits rule with real-time validation

- **WHEN** a teacher types an expression in the CodeMirror editor
- **THEN** the editor SHALL invoke WASM `validate()` within 50ms debounce and display error markers inline for any diagnostics

#### Scenario: Teacher gets autocomplete suggestions

- **WHEN** a teacher triggers autocomplete (Ctrl+Space or typing) in the CodeMirror editor
- **THEN** the editor SHALL invoke WASM `complete()` and display a dropdown with contextually relevant suggestions including variable names, operators, and function signatures

### Requirement: BadgeDefinition binding to trigger rule

The system SHALL allow a BadgeDefinition to bind to a TriggerRule via the `trigger_rule_id` field. The `trigger_key` and `trigger_rule_id` fields SHALL be mutually exclusive — the system SHALL reject any attempt to set both simultaneously. A single TriggerRule MAY be bound to multiple BadgeDefinitions.

#### Scenario: Badge bound to DSL trigger rule

- **WHEN** a teacher creates a badge with `trigger_rule_id` set to a valid TriggerRule ID
- **THEN** the system SHALL persist the badge definition with the binding

#### Scenario: Mutual exclusion enforced

- **WHEN** a teacher attempts to set both `trigger_key` and `trigger_rule_id` on a BadgeDefinition
- **THEN** the system SHALL return HTTP 422 indicating the fields are mutually exclusive

### Requirement: DSL trigger evaluation in badge award flow

The system SHALL evaluate DSL trigger rules as part of `evaluate_triggers_for_event()`. For each BadgeDefinition with a `trigger_rule_id`, the system SHALL load the bound TriggerRule, build an `EvalContext` from class-scoped student data, and call `dsl_engine.evaluate()`. If the result is `true` and the student does not already hold the badge, the badge SHALL be awarded. The `EvalContext` SHALL be constructed by the service layer using only data scoped to the badge's `class_id`.

#### Scenario: DSL rule triggers badge award

- **WHEN** a reward event occurs and a BadgeDefinition is bound to a TriggerRule with expression `checkin_streak >= 7`, and the student's checkin_streak is 7
- **THEN** the system SHALL evaluate the expression to `true` and award the badge

#### Scenario: DSL rule does not trigger for unmet condition

- **WHEN** a reward event occurs and a BadgeDefinition is bound to a TriggerRule with expression `checkin_streak >= 7`, and the student's checkin_streak is 3
- **THEN** the system SHALL evaluate the expression to `false` and NOT award the badge

#### Scenario: Inactive rule skipped

- **WHEN** a reward event occurs and a BadgeDefinition is bound to a TriggerRule with `is_active: false`
- **THEN** the system SHALL skip evaluation of that rule
