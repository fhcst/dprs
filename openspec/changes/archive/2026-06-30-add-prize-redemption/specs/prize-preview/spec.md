## ADDED Requirements

### Requirement: Teacher prize management HTML page

The system SHALL serve a teacher-facing prize management page at `GET /pages/classes/{class_id}/prizes/manage`. The page SHALL require that the requester can manage the class (`can_manage_class`); a requester who cannot manage the class SHALL receive HTTP 403. The page SHALL reuse the existing prize create, list, patch, and delete endpoints to: list all prizes for the class (including hidden ones), create a prize with title, description, point cost, and visibility, toggle a prize's visibility, and delete a prize. The create and patch endpoints SHALL reject a non-positive `point_cost` (`point_cost <= 0`) with a 4xx error and SHALL NOT persist such a value, so that a prize visible to students always satisfies the redemption invariant `point_cost > 0`. The management create form SHALL default the point-cost input to a positive value and SHALL NOT default it to zero.

#### Scenario: Teacher opens the prize management page

- **WHEN** a teacher who can manage the class opens `GET /pages/classes/{class_id}/prizes/manage`
- **THEN** the system SHALL render an HTML page listing all prizes for that class, including hidden ones, with controls to create, toggle visibility, and delete

#### Scenario: Non-managing user is forbidden

- **WHEN** a user who cannot manage the class opens `GET /pages/classes/{class_id}/prizes/manage`
- **THEN** the system SHALL return HTTP 403

#### Scenario: Teacher creates a prize through the UI

- **WHEN** a teacher submits the management page's create form with a title, description, point cost, and visibility
- **THEN** the system SHALL create the prize via the existing create endpoint and the new prize SHALL appear in the management list

#### Scenario: Non-positive point cost is rejected on create or patch

- **WHEN** a teacher who can manage the class calls the create or patch endpoint with `point_cost <= 0`
- **THEN** the system SHALL reject the request with a 4xx error and SHALL NOT create or update the prize to a non-positive cost, preventing a visible-but-never-redeemable prize

### Requirement: Prize mutation endpoints enforce ownership and permission

The prize mutation endpoints `PATCH /prizes/{prize_id}` and `DELETE /prizes/{prize_id}` SHALL require the `MANAGE_TASKS` permission and SHALL authorize the caller against the prize's own class. The endpoints MUST derive the class from the loaded prize record (`prize.class_id`) rather than trusting any caller-supplied class identifier, and SHALL reject a caller who cannot manage that class with HTTP 403. A request lacking the `MANAGE_TASKS` permission SHALL be rejected with HTTP 403.

#### Scenario: Cross-teacher mutation is forbidden

- **WHEN** teacher A calls `PATCH /prizes/{prize_id}` or `DELETE /prizes/{prize_id}` for a prize whose class is managed only by teacher B
- **THEN** the system SHALL return HTTP 403 and SHALL NOT modify or delete the prize

#### Scenario: Missing MANAGE_TASKS permission is forbidden

- **WHEN** a caller without the `MANAGE_TASKS` permission calls `PATCH /prizes/{prize_id}` or `DELETE /prizes/{prize_id}`
- **THEN** the system SHALL return HTTP 403
