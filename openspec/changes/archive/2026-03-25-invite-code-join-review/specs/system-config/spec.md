## MODIFIED Requirements

### Requirement: SystemConfig document stores global settings

The system SHALL maintain a single `SystemConfig` Beanie Document in MongoDB with a fixed `_id` of `"global"`. This document MUST store system-level settings including site name, admin email, and join request reject cooldown hours. The `join_request_reject_cooldown_hours` field MUST be an integer with a default value of `24`. A value of `0` SHALL indicate no cooldown restriction (students can reapply immediately after rejection).

#### Scenario: SystemConfig is created during setup

- **WHEN** the administrator completes the setup wizard form
- **THEN** a `SystemConfig` document with `_id = "global"` MUST be written to MongoDB, with `join_request_reject_cooldown_hours` defaulting to `24`

#### Scenario: SystemConfig is retrieved on startup

- **WHEN** the application starts and Redis flag `system:configured` is `"true"`
- **THEN** the system SHALL load the `SystemConfig` document from MongoDB and make it available via `app.state.system_config`, including the `join_request_reject_cooldown_hours` value

---

### Requirement: System config update API

The system SHALL provide `PUT /admin/system` accepting a JSON body with updatable fields (`site_name`, `admin_email`, `join_request_reject_cooldown_hours`). The endpoint MUST require `WRITE_SYSTEM` permission. On success, the MongoDB `SystemConfig` document MUST be updated and `app.state.system_config` MUST reflect the new values immediately. The `WebPage` global context `site_name` MUST also be refreshed via `webpage_context_update`. The `join_request_reject_cooldown_hours` field MUST accept only non-negative integer values; negative values MUST be rejected with HTTP 422.

#### Scenario: Admin updates site name

- **WHEN** a user with `WRITE_SYSTEM` sends `PUT /admin/system` with a new `site_name`
- **THEN** the MongoDB document MUST be updated, `app.state.system_config.site_name` MUST reflect the new value, and subsequent page renders SHALL use the new site name

#### Scenario: Admin updates join request cooldown

- **WHEN** a user with `WRITE_SYSTEM` sends `PUT /admin/system` with `join_request_reject_cooldown_hours` set to `48`
- **THEN** the MongoDB document MUST be updated and all subsequent join request cooldown checks SHALL use the new value of `48` hours

#### Scenario: Admin disables join request cooldown

- **WHEN** a user with `WRITE_SYSTEM` sends `PUT /admin/system` with `join_request_reject_cooldown_hours` set to `0`
- **THEN** the system MUST allow students to reapply to any class immediately after rejection

#### Scenario: Negative cooldown value is rejected

- **WHEN** a user with `WRITE_SYSTEM` sends `PUT /admin/system` with `join_request_reject_cooldown_hours` set to a negative value
- **THEN** the system MUST return HTTP 422

#### Scenario: Unauthorized update is rejected

- **WHEN** a user without `WRITE_SYSTEM` sends `PUT /admin/system`
- **THEN** the system SHALL return HTTP 403
