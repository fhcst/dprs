## ADDED Requirements

### Requirement: Teacher sidebar includes badge management link

The teacher sidebar in `base.html` SHALL include a "徽章管理" navigation link within the active class tool links section. The link SHALL point to the `badges_manage_page` route for the active class. The link SHALL only be visible when `active_class.id` is set (same condition as the other class tool links). The link SHALL use an icon consistent with the badge concept (e.g., a star or trophy icon using Heroicons outline style).

#### Scenario: Teacher sees badge management link in sidebar

- **WHEN** a teacher views any page with the sidebar and has an active class selected
- **THEN** the sidebar SHALL display a "徽章管理" link under the active class tool links section

#### Scenario: Badge management link navigates to correct page

- **WHEN** a teacher clicks the "徽章管理" link in the sidebar
- **THEN** the browser SHALL navigate to `/pages/classes/{active_class_id}/badges` (the `badges_manage_page` route)

#### Scenario: Badge management link hidden when no active class

- **WHEN** a teacher views a page without an active class selected
- **THEN** the sidebar SHALL NOT display the "徽章管理" link
