## ADDED Requirements

### Requirement: Class stores Discord message template defaults

The Class model SHALL include an optional embedded field `discord_template` containing three string sub-fields: `title_format`, `description_template`, and `footer_text`. All sub-fields SHALL default to empty string. When `discord_template` is `None` or a sub-field is empty, the system SHALL fall back to the system default for that sub-field.

System defaults:
- `title_format`: `{task_name} — {date}`
- `description_template`: truncated task description (first 200 characters)
- `footer_text`: system `site_name` value

#### Scenario: New class has no discord_template

- **WHEN** a new class is created
- **THEN** the `discord_template` field SHALL be `None`

#### Scenario: Class with partial template uses fallback for empty sub-fields

- **WHEN** a class has `discord_template.title_format` set to a non-empty string and `discord_template.description_template` set to empty string
- **THEN** the system SHALL use the class title_format for the embed title and SHALL fall back to the system default for the embed description

---

### Requirement: Teacher sets class Discord template via API

The system SHALL provide a `PATCH /classes/{class_id}/discord-template` endpoint that accepts a JSON body with optional fields `title_format`, `description_template`, and `footer_text`. Only users who satisfy `can_manage_class` for the given class SHALL be authorized to call this endpoint. Omitted fields SHALL NOT be modified. An empty string value SHALL clear that sub-field (reverting to fallback).

#### Scenario: Teacher sets all three template fields

- **WHEN** an authorized teacher sends `PATCH /classes/{class_id}/discord-template` with `{"title_format": "{task_name}", "description_template": "Details: {description}", "footer_text": "My Class"}`
- **THEN** the system SHALL store all three values in the class `discord_template` field and return HTTP 200

#### Scenario: Teacher clears a single field

- **WHEN** an authorized teacher sends `PATCH /classes/{class_id}/discord-template` with `{"footer_text": ""}`
- **THEN** the system SHALL set `discord_template.footer_text` to empty string and SHALL NOT modify the other sub-fields

#### Scenario: Unauthorized user cannot set template

- **WHEN** a user who does not satisfy `can_manage_class` for class C sends `PATCH /classes/C/discord-template`
- **THEN** the system SHALL return HTTP 403

#### Scenario: Partial update preserves existing fields

- **WHEN** a class has `discord_template.title_format` set to `"Custom: {task_name}"` and an authorized teacher sends `PATCH /classes/{class_id}/discord-template` with `{"footer_text": "New Footer"}`
- **THEN** the system SHALL update `footer_text` to `"New Footer"` and SHALL preserve the existing `title_format` value

---

### Requirement: Task assignment supports per-task template overrides

The task assignment form SHALL include an advanced options section (collapsed by default) with three fields: title override, description override, and footer override. These fields SHALL be pre-filled with the class default template values. When submitted, non-empty override values SHALL take precedence over the class default for that task's Discord embed.

#### Scenario: Teacher overrides title at task level

- **WHEN** a teacher assigns a task with a non-empty title override value
- **THEN** the Discord embed title SHALL use the task-level override instead of the class default

#### Scenario: Teacher leaves override empty to use class default

- **WHEN** a teacher assigns a task with the title override field left empty and the class has a `discord_template.title_format` set
- **THEN** the Discord embed title SHALL use the class default `title_format`

#### Scenario: Advanced options are collapsed by default

- **WHEN** a teacher opens the task assignment form
- **THEN** the advanced options section containing template overrides SHALL be collapsed (hidden) by default

#### Scenario: Override fields are pre-filled from class defaults

- **WHEN** a teacher expands the advanced options section for a class that has `discord_template` set
- **THEN** the title, description, and footer fields SHALL be pre-filled with the class default values

---

### Requirement: Template variable interpolation

The system SHALL support variable interpolation in template fields using `{variable_name}` syntax (Python `str.format_map` style). The available variables SHALL be: `{task_name}`, `{date}`, `{class_name}`, and `{description}`. If a template contains an undefined variable name, the system SHALL leave the placeholder as-is in the output and SHALL log a warning. If a template contains malformed brace syntax, the system SHALL use the raw template text without interpolation and SHALL log a warning.

#### Scenario: Valid variables are replaced

- **WHEN** a template contains `{task_name} — {date}` and the task name is "Math Homework" and the date is "2026-03-25"
- **THEN** the rendered output SHALL be `Math Homework — 2026-03-25`

#### Scenario: Undefined variable is left as-is

- **WHEN** a template contains `{task_name} by {author}` where `{author}` is not a recognized variable
- **THEN** the rendered output SHALL be `Math Homework by {author}` and the system SHALL log a warning

#### Scenario: Malformed braces fall back to raw text

- **WHEN** a template contains `{task_name} price: ${ amount` with unmatched braces
- **THEN** the system SHALL use the raw template text as the output and SHALL log a warning

---

### Requirement: Discord embed field length enforcement

Before sending an embed to the Discord API, the system SHALL enforce the following length limits by truncating and appending `...`:
- Embed title: 256 characters maximum
- Embed description: 4096 characters maximum
- Embed footer text: 2048 characters maximum

#### Scenario: Title exceeding 256 characters is truncated

- **WHEN** the rendered title text is 300 characters long
- **THEN** the system SHALL truncate it to 253 characters followed by `...` (total 256 characters)

#### Scenario: Description within limit is not modified

- **WHEN** the rendered description text is 500 characters long
- **THEN** the system SHALL send it as-is without truncation

---

### Requirement: Help modal displays available variables and Discord Markdown syntax

The UI SHALL provide a `(?)` help button next to the description template textarea. Clicking this button SHALL open a modal containing: (1) a table of available template variables and their descriptions, (2) a Discord Markdown syntax cheat sheet listing supported formatting, and (3) a list of unsupported syntax that teachers SHALL avoid.

Supported Discord Markdown: bold (`**`), italic (`*` / `_`), underline (`__`), strikethrough (`~~`), spoiler (`||`), headers (`#` / `##` / `###`), subtext (`-#`), code blocks (`` ` `` and ` ``` ` with syntax highlighting), blockquotes (`>` / `>>>`), lists (`-` / `*` and `1.`), masked links (`[text](url)`), timestamps (`<t:unix:flag>`).

NOT supported: tables, images (`![]()`), horizontal rules, HTML tags, checkboxes, footnotes.

#### Scenario: Help modal opens on button click

- **WHEN** a teacher clicks the `(?)` button next to the description template textarea
- **THEN** the system SHALL display a modal with variable reference, Markdown syntax guide, and unsupported syntax warnings

#### Scenario: Help modal lists all available variables

- **WHEN** the help modal is displayed
- **THEN** the modal SHALL list the variables `{task_name}`, `{date}`, `{class_name}`, and `{description}` with a description of each
