## ADDED Requirements

### Requirement: Button visual hierarchy

The system SHALL maintain a clear visual distinction between primary CTA buttons, secondary buttons, and active tab indicators. Primary CTA buttons SHALL use `bg-brand-600` with `rounded-lg`. Active filter tabs SHALL use a visually distinct style (such as `bg-brand-100 text-brand-700 border-brand-300`) that is clearly different from primary CTA buttons.

#### Scenario: Submission review page displays tabs and approve button

- **WHEN** the submission review page renders with active filter tabs and approve buttons
- **THEN** the active tab style SHALL be visually distinct from the approve CTA button
- **THEN** a user SHALL be able to distinguish tabs from action buttons at a glance

### Requirement: Content max-width constraint

All page content areas (excluding admin tables that require full width) SHALL be constrained to a maximum width. Content-heavy pages (submission review, class history, learning history, points management) SHALL use `max-w-5xl` or narrower. Form pages SHALL use `max-w-3xl` or narrower.

#### Scenario: Submission review page on a 1920px monitor

- **WHEN** the submission review page renders on a 1920px wide viewport
- **THEN** the content area SHALL NOT exceed the defined max-width
- **THEN** the content SHALL be horizontally centered within the viewport

### Requirement: Mobile body text minimum size

On viewports narrower than 640px, primary body text SHALL be at least 16px (`text-base` in Tailwind). Secondary/meta text (timestamps, muted labels) SHALL be at least 14px (`text-sm`).

#### Scenario: Student reads task description on mobile

- **WHEN** a student views a task description on a viewport narrower than 640px
- **THEN** the body text font size SHALL be at least 16px

### Requirement: Consistent card styling

All card components across the system SHALL use consistent styling: `rounded-xl` border radius, `border border-gray-200 dark:border-gray-800`, and `p-5` padding. The login page card SHALL follow the same radius (`rounded-xl`, not `rounded-2xl`).

#### Scenario: Dashboard stat cards render

- **WHEN** dashboard stat cards render
- **THEN** each card SHALL use `rounded-xl` border radius and consistent padding

### Requirement: Consistent success color

All success indicators throughout the system SHALL use the `green` color palette (not `emerald`). This applies to success banners, check-in badges, approved status badges, and positive point indicators.

#### Scenario: Settings page shows success message

- **WHEN** a user successfully updates their display name on the settings page
- **THEN** the success banner SHALL use `green-50`/`green-700` colors (not emerald)

### Requirement: Terminology standardization

All user-facing text SHALL use consistent terminology: "任務" (not "作業") for tasks/assignments, and "通過" (not "確認") for the approval action. The submission review filter tab for approved items SHALL read "已通過".

#### Scenario: Submission review page displays filter tabs

- **WHEN** the submission review page renders
- **THEN** the approved filter tab SHALL read "已通過" (not "已確認")

#### Scenario: Dashboard displays teacher tool links

- **WHEN** the teacher dashboard renders class cards with tool links
- **THEN** the submission review link SHALL read "任務審閱" (not "作業審閱")
