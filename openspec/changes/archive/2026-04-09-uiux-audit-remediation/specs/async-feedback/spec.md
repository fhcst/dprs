## ADDED Requirements

### Requirement: Form POST loading state

All form submit buttons SHALL enter a disabled state when the form is submitted. The button text SHALL be replaced with a spinner icon and "處理中..." text. The button SHALL remain disabled until the page reloads or the request completes.

#### Scenario: User submits the login form

- **WHEN** a user clicks the "登入" submit button
- **THEN** the button SHALL become disabled immediately
- **THEN** the button SHALL display a spinning indicator and "處理中..." text
- **THEN** the button SHALL remain disabled until the page navigates or reloads

#### Scenario: User submits the check-in form

- **WHEN** a user clicks the "簽到" button
- **THEN** the button SHALL become disabled immediately
- **THEN** the button SHALL display a loading indicator

### Requirement: JavaScript fetch loading state utility

The system SHALL provide a global `withLoading(button, asyncFunction)` utility function. When called, it SHALL disable the button, replace its content with a spinner, execute the async function, and restore the button afterward regardless of success or failure.

#### Scenario: Teacher approves a submission using withLoading

- **WHEN** a teacher clicks "通過" and the operation uses `withLoading`
- **THEN** the button SHALL be disabled and show a spinner during the fetch request
- **THEN** after the fetch completes (success or error), the button SHALL be restored to its original state

#### Scenario: Fetch fails with network error

- **WHEN** `withLoading` is called and the fetch request fails due to a network error
- **THEN** the button SHALL be restored to its original clickable state
- **THEN** an error toast SHALL be displayed

### Requirement: Destructive action confirmation

The following destructive actions SHALL require a confirmation dialog before execution: delete feed post, regenerate invite code, revoke badge, deduct points, delete user (admin). The confirmation dialog SHALL clearly describe the irreversible consequence.

#### Scenario: User attempts to delete a feed post

- **WHEN** a user clicks the delete button on a feed post
- **THEN** a confirmation dialog SHALL appear with the message describing the action
- **THEN** the post SHALL NOT be deleted until the user confirms

#### Scenario: Teacher regenerates invite code

- **WHEN** a teacher clicks "重新產生" on the invite code
- **THEN** a confirmation dialog SHALL appear warning that the old code will be invalidated
- **THEN** the code SHALL NOT change until the user confirms

#### Scenario: User cancels a destructive action

- **WHEN** a confirmation dialog is shown and the user clicks "取消" or presses Escape
- **THEN** the action SHALL NOT be executed
- **THEN** the dialog SHALL close and focus SHALL return to the trigger element

### Requirement: Unified error feedback pattern

Form-level errors SHALL use inline alert banners at the top of the form. Async operation errors SHALL use toast notifications. All error displays SHALL include an icon, descriptive text, and a clear visual distinction from success messages.

#### Scenario: Form POST returns an error

- **WHEN** a form submission fails and the page reloads with an error
- **THEN** an inline alert banner with `role="alert"` SHALL appear at the top of the form content
- **THEN** the banner SHALL use red styling with a warning icon

#### Scenario: Async fetch operation fails

- **WHEN** a JavaScript fetch operation fails
- **THEN** a toast notification SHALL appear using `Toast.error(message)`
- **THEN** the toast SHALL auto-dismiss after 5 seconds
