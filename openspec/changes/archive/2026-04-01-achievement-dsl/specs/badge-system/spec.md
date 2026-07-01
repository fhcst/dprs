## MODIFIED Requirements

### Requirement: Badge definition by teacher

Teachers SHALL be able to define badges for a class. Each badge definition MUST include: name, description (Markdown format), icon identifier, and optionally one of: a registered BadgeTrigger key (`trigger_key`), a DSL trigger rule reference (`trigger_rule_id`), or neither (manual award only). The `trigger_key` and `trigger_rule_id` fields SHALL be mutually exclusive.

#### Scenario: Teacher creates a badge with DSL trigger rule

- **WHEN** a teacher submits a badge definition with a name and a `trigger_rule_id` referencing a valid TriggerRule
- **THEN** the system SHALL persist the badge definition with the DSL trigger binding for that class

#### Scenario: Teacher creates a badge with code trigger key

- **WHEN** a teacher submits a badge definition with a name and a `trigger_key` referencing a registered BadgeTrigger
- **THEN** the system SHALL persist the badge definition for that class

#### Scenario: Teacher creates a manual-only badge

- **WHEN** a teacher submits a badge definition with neither `trigger_key` nor `trigger_rule_id`
- **THEN** the system SHALL persist the badge definition as manual-award only

#### Scenario: Mutual exclusion enforced on badge creation

- **WHEN** a teacher submits a badge definition with both `trigger_key` and `trigger_rule_id` set
- **THEN** the system SHALL reject the request with HTTP 422

### Requirement: Badge awarded automatically on trigger

The system SHALL evaluate all registered BadgeTriggers and all active DSL TriggerRules after each reward event. For code triggers: if a BadgeTrigger's condition is met and the student does not already hold that badge, the badge SHALL be awarded automatically. For DSL triggers: if a TriggerRule's expression evaluates to `true` via `dsl_engine.evaluate()` and the student does not already hold that badge, the badge SHALL be awarded automatically. Inactive TriggerRules (`is_active: false`) SHALL be skipped.

#### Scenario: Badge awarded after code trigger condition met

- **WHEN** a reward event occurs and a BadgeTrigger's condition evaluates to true for a student who does not yet hold the badge
- **THEN** the system SHALL create a badge award record for that student

#### Scenario: Badge awarded after DSL trigger condition met

- **WHEN** a reward event occurs and a TriggerRule's DSL expression evaluates to true for a student who does not yet hold the badge
- **THEN** the system SHALL create a badge award record for that student with `awarded_by: "system"`

#### Scenario: Badge not awarded if already held

- **WHEN** a reward event occurs and the student already holds the badge
- **THEN** the system SHALL NOT create a duplicate award record

#### Scenario: Inactive DSL rule skipped during evaluation

- **WHEN** a reward event occurs and a BadgeDefinition is bound to a TriggerRule with `is_active: false`
- **THEN** the system SHALL skip evaluation of that rule and NOT award the badge
