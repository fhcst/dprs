## ADDED Requirements

### Requirement: Class model includes Discord template embedded field

The Class model SHALL include an optional field `discord_template` (embedded document, nullable, default `None`) with sub-fields `title_format` (string), `description_template` (string), and `footer_text` (string). This field SHALL be stored as an embedded document within the class record, not as a separate collection.

#### Scenario: Existing classes are unaffected

- **WHEN** the system reads a class document that was created before the `discord_template` field existed
- **THEN** the `discord_template` field SHALL resolve to `None` and the system SHALL operate using system default template values

#### Scenario: discord_template field is not exposed to students

- **WHEN** a student views class information
- **THEN** the `discord_template` field SHALL NOT be included in any student-facing API response or template
