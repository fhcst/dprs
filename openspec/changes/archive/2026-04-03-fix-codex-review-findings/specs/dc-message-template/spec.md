## MODIFIED Requirements

### Requirement: Task assignment supports per-task template overrides

The `ScheduleRuleRequest` model SHALL include optional fields `dc_title_override`, `dc_desc_override`, and `dc_footer_override` (all `Optional[str]`). When a schedule rule is created with these fields set, the system SHALL pass the override values to the Discord webhook renderer so that the scheduled Discord message uses the custom title, description, and footer instead of defaults.

#### Scenario: Schedule rule created with Discord overrides

- **WHEN** a teacher creates a schedule rule with `dc_title_override` set to "特別公告"
- **THEN** the Discord webhook message SHALL use "特別公告" as the title instead of the default template title

#### Scenario: Schedule rule created without Discord overrides

- **WHEN** a teacher creates a schedule rule without setting any `dc_*_override` fields
- **THEN** the Discord webhook message SHALL use the default template values
