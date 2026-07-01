## ADDED Requirements

### Requirement: Paginated student enumeration API

The system SHALL provide a paginated API endpoint `GET /classes/{class_id}/invite/students` that returns all users with `STUDENT` identity tag who are NOT members of class `{class_id}`. The endpoint MUST require class management authorization (`can_manage_class`). The response MUST include `students` (array), `total` (integer), `offset` (integer), and `limit` (integer). Each student object MUST include `user_id`, `display_name`, `name`, `class_name`, `seat_number`, and `tags`. The default sort order MUST be `class_name` ASC then `seat_number` ASC. The default `limit` MUST be 100.

#### Scenario: First page of students

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/students?offset=0&limit=100`
- **THEN** the system SHALL return the first 100 non-member students sorted by `class_name` ASC then `seat_number` ASC, with `total` reflecting the full count of non-member students

#### Scenario: Subsequent page

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/students?offset=100&limit=100` and `total` is 250
- **THEN** the system SHALL return students 101-200 in the same sort order

#### Scenario: Offset beyond total

- **WHEN** an authorized teacher sends `GET /classes/{class_id}/invite/students?offset=300&limit=100` and `total` is 250
- **THEN** the system SHALL return an empty `students` array with `total` still reflecting 250

#### Scenario: Unauthorized access

- **WHEN** a user who does not satisfy `can_manage_class` for class `{class_id}` sends `GET /classes/{class_id}/invite/students`
- **THEN** the system MUST return HTTP 403

### Requirement: Grade-level grouping by class_name prefix

The invite UI SHALL group students by grade level using the first character of `class_name` as the group key (e.g., `class_name` "301班" yields grade "3"). Within each grade group, students MUST be further grouped by full `class_name`. Within each `class_name` group, students MUST be sorted by `seat_number` ASC. Students with empty `class_name` MUST appear in a group labeled "未分類".

#### Scenario: Students grouped by grade and class

- **WHEN** a teacher views the invite panel with students having `class_name` values "301班", "302班", and "201班"
- **THEN** the UI SHALL display grade "3" containing groups "301班" and "302班", and grade "2" containing group "201班"

#### Scenario: Students with empty class_name

- **WHEN** a teacher views the invite panel and some students have empty `class_name`
- **THEN** those students SHALL appear in a group labeled "未分類"

### Requirement: Tag-based grouping mode

The invite UI SHALL support an alternative grouping mode where students are grouped by their `tags` values. A student with multiple tags MUST appear in each corresponding tag group. Students with no tags MUST appear in a group labeled "無標籤". The teacher MUST be able to switch between class-based grouping and tag-based grouping without losing selection state.

#### Scenario: Switch to tag-based grouping

- **WHEN** a teacher selects the "按標籤" grouping mode
- **THEN** the UI SHALL re-render students grouped by tag values, with students appearing in multiple groups if they have multiple tags

#### Scenario: Selection state preserved across grouping switch

- **WHEN** a teacher selects 3 students in class-based grouping mode and switches to tag-based grouping mode
- **THEN** those 3 students SHALL remain selected (checked) in the tag-based view

### Requirement: Category select-all

Each group header in the invite panel SHALL include a "全選" checkbox. Checking the group checkbox MUST select all currently visible (not filtered out) students within that group. Unchecking MUST deselect all students in that group. When some students in a group are selected and others are not, the group checkbox MUST display an indeterminate state.

#### Scenario: Select all in a group

- **WHEN** a teacher checks the "全選" checkbox on a group containing 15 visible students
- **THEN** all 15 students in that group SHALL become selected

#### Scenario: Indeterminate state

- **WHEN** a teacher manually selects 5 out of 15 students in a group
- **THEN** the group's "全選" checkbox SHALL display in indeterminate state

#### Scenario: Select-all respects search filter

- **WHEN** a teacher has a search filter active that hides 10 of 15 students in a group and checks "全選" on that group
- **THEN** only the 5 visible students SHALL be selected

### Requirement: Client-side search filter

The invite panel SHALL include a search input that filters the displayed student list in real time without additional API calls. The filter MUST match against `name`, `display_name`, `class_name`, `seat_number` (as string), and `tags` values (case-insensitive substring match). Groups with no matching students MUST be hidden. If data has not been fully loaded when the teacher starts typing, the system MUST complete loading all remaining pages before applying the filter.

#### Scenario: Search filters across all fields

- **WHEN** a teacher types "301" in the search input
- **THEN** the UI SHALL show only students whose `name`, `display_name`, `class_name`, seat number string, or any tag value contains "301"

#### Scenario: Search triggers full data load

- **WHEN** a teacher types a search query while only 100 of 250 students have been loaded
- **THEN** the system SHALL immediately load the remaining 150 students, then apply the filter to the complete dataset

#### Scenario: Empty groups hidden during search

- **WHEN** a search filter is active and a group has zero matching students
- **THEN** that group SHALL be hidden from the UI

### Requirement: Lazy loading with automatic continuation

The invite panel MUST load students in pages (default 100 per page). The first page MUST be requested on page load. Subsequent pages MUST be requested automatically without user interaction until all students are loaded. The UI MUST display a loading indicator while pages are being fetched. The total count of available students MUST be displayed.

#### Scenario: Automatic pagination

- **WHEN** the invite panel loads and the API returns `total: 250` with `limit: 100`
- **THEN** the system SHALL automatically request pages at offset 100 and 200 to complete the dataset

#### Scenario: Loading indicator

- **WHEN** pages are still being fetched
- **THEN** the UI SHALL display a loading indicator showing progress (e.g., "載入中 100/250")
