## MODIFIED Requirements

### Requirement: Task assignment optionally syncs to Discord

The system SHALL send a Discord embed message to the class Webhook URL when a teacher assigns a task and opts in to Discord sync. The embed content SHALL be rendered using the template resolution chain: task-level override > class default template > system default. The system SHALL perform variable interpolation on the resolved template before sending.

#### Scenario: Message sent on opt-in assignment

- **WHEN** a teacher assigns a task and the "同步到 Discord" option is checked and the class has a Webhook URL
- **THEN** the system SHALL send a POST request to the Webhook URL with an embed whose title, description, and footer are resolved through the template fallback chain and variable interpolation

#### Scenario: No message sent when opt-out

- **WHEN** a teacher assigns a task without checking the "同步到 Discord" option
- **THEN** the system SHALL NOT send any Discord message

#### Scenario: No message sent when no Webhook URL

- **WHEN** a class has no Webhook URL configured and a teacher assigns a task with sync checked
- **THEN** the system SHALL silently skip the Discord send

#### Scenario: Embed uses system defaults when no template is configured

- **WHEN** a teacher assigns a task with Discord sync enabled, the class has no `discord_template` set, and no task-level overrides are provided
- **THEN** the embed title SHALL be the task name, the embed description SHALL be the task description truncated to 200 characters, and the embed footer SHALL be the system site_name value
