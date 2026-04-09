## ADDED Requirements

### Requirement: Teacher mobile bottom tab bar

On viewports narrower than 768px, users with teacher permissions SHALL see a bottom tab bar with the following items: Home (首頁), Review (審閱), Attendance (出席), Class (班級), More (更多). The "More" tab SHALL open a bottom sheet with additional management links.

#### Scenario: Teacher views dashboard on mobile

- **WHEN** a teacher loads the dashboard on a viewport narrower than 768px
- **THEN** a bottom tab bar SHALL be visible with 5 items: 首頁, 審閱, 出席, 班級, 更多
- **THEN** "審閱" SHALL link to the submission review page of the teacher's first class
- **THEN** "出席" SHALL link to the attendance management page of the teacher's first class

#### Scenario: Teacher taps "More" tab

- **WHEN** a teacher taps the "更多" tab on mobile
- **THEN** a bottom sheet SHALL open listing additional management links: 積分管理, 徽章管理, 簽到設定, Trigger Rules, 個人設定

#### Scenario: Teacher with multiple classes uses mobile nav

- **WHEN** a teacher with multiple classes taps "審閱" on mobile
- **THEN** the system SHALL navigate to the submission review page of the first (most recently accessed or first-created) class
- **THEN** the submission review page SHALL allow switching to other classes

### Requirement: Student mobile bottom tab bar

On viewports narrower than 768px, users with student-only permissions SHALL see a bottom tab bar with exactly 4 items: Home (首頁), Badges (徽章), History (歷程), Settings (設定). There SHALL be no duplicate items.

#### Scenario: Student views dashboard on mobile

- **WHEN** a student loads the dashboard on a viewport narrower than 768px
- **THEN** a bottom tab bar SHALL be visible with 4 items: 首頁, 徽章, 歷程, 設定
- **THEN** each item SHALL link to a distinct page

### Requirement: Sidebar collapse state persistence

The desktop sidebar collapse/expand state SHALL be persisted in `localStorage`. When a user navigates to a new page, the sidebar SHALL restore its previous collapsed/expanded state.

#### Scenario: User collapses sidebar and navigates

- **WHEN** a user collapses the sidebar and then navigates to another page
- **THEN** the sidebar SHALL remain collapsed on the new page

#### Scenario: User expands sidebar and navigates

- **WHEN** a user expands the sidebar and then navigates to another page
- **THEN** the sidebar SHALL remain expanded on the new page

### Requirement: Tablet horizontal nav overflow handling

On tablet viewports (768px to 1023px), the horizontal navigation bar SHALL handle overflow gracefully. When class names exceed the available width, the nav SHALL be horizontally scrollable.

#### Scenario: Teacher with 5 classes on tablet

- **WHEN** a teacher with 5 classes (each with long names) views the app on a tablet
- **THEN** the horizontal nav SHALL be scrollable horizontally
- **THEN** no nav items SHALL overflow outside the viewport

### Requirement: Consistent breadcrumb navigation

All sub-pages (pages deeper than the dashboard) SHALL include a breadcrumb navigation showing the path from dashboard to the current page. Breadcrumbs SHALL use the `{% block breadcrumb %}` template block defined in the base template.

#### Scenario: Student views class history page

- **WHEN** a student navigates to a class history page
- **THEN** a breadcrumb SHALL display: 儀表板 > {class_name} > 任務歷程

#### Scenario: Teacher views submission review page

- **WHEN** a teacher navigates to the submission review page
- **THEN** a breadcrumb SHALL display: 儀表板 > {class_name} > 任務審查
