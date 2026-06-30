# modal-system Specification

## Purpose

Defines the shared non-blocking modal component that replaces native browser dialogs (`alert`, `confirm`) across all application pages.

## Requirements

### Requirement: Global non-blocking modal replaces browser dialogs

The application SHALL provide a shared, non-blocking Modal component available to all pages via `window.Modal`. All pages that previously called `alert()` or `confirm()` SHALL use `Modal.alert()` or `Modal.confirm()` instead. The modal component SHALL be defined in `shared/base.html` and SHALL be available without any additional import.

#### Scenario: Confirm modal shown with callback

- **WHEN** a page calls `Modal.confirm("Are you sure?", onConfirm, onCancel)`
- **THEN** a modal overlay appears with the message text, a "確認" button, and a "取消" button
- **AND** clicking "確認" calls `onConfirm` and closes the modal
- **AND** clicking "取消" or the backdrop calls `onCancel` (if provided) and closes the modal
- **AND** the page remains responsive while the modal is open (non-blocking)

#### Scenario: Alert modal shown with callback

- **WHEN** a page calls `Modal.alert("Operation failed.")`
- **THEN** a modal overlay appears with the message text and a "確認" button
- **AND** clicking "確認" closes the modal
- **AND** no `onCancel` handler is required

<!-- @trace
source: ui-polish-and-fixes
updated: 2026-03-19
-->

---
### Requirement: All existing browser dialog calls replaced

Every call to `window.confirm()` or `window.alert()` in HTML templates SHALL be replaced with the corresponding `Modal.confirm()` or `Modal.alert()` call. After this change, no template SHALL contain a direct call to the native browser dialog functions.

#### Scenario: Delete confirmation uses modal

- **WHEN** a user clicks a "刪除" or "移除" button
- **THEN** `Modal.confirm()` is called (not `window.confirm()`)
- **AND** the deletion proceeds only if the user clicks "確認" in the modal

<!-- @trace
source: ui-polish-and-fixes
updated: 2026-03-19
-->

---
### Requirement: Dialog form modals invoke the confirm callback before teardown

The shared Modal component SHALL support form modals via `Modal.dialog({ title, content, onConfirm, ... })`, where `content` is injected into the modal body and `onConfirm` is an async callback. When the user confirms a dialog, the Modal component SHALL invoke `onConfirm` while the dialog body and every element it contains remain present in the DOM. The Modal component SHALL hide and clear the dialog body only after the `onConfirm` promise settles.

The return value of `onConfirm` SHALL control closing: returning `false`, returning any object carrying a truthy `__modalKeepOpen` property, throwing, or rejecting SHALL keep the dialog open with its body (including any in-modal message element) preserved; resolving to any other value (including `undefined` from a bare `return;`) SHALL close and clear the dialog. (`Modal.KEEP_OPEN` is an explicit, self-documenting keep-open sentinel — an object with `__modalKeepOpen: true` — provided alongside `false` so a future caller can keep a dialog open without the "bare `return;` accidentally closes" foot-gun. Keep-open SHALL be detected structurally on the `__modalKeepOpen` property rather than by reference equality with the sentinel, so a caller returning a shape-equivalent `{ __modalKeepOpen: true }` literal keeps the dialog open too.) An error thrown inside `onConfirm` SHALL NOT surface as an unhandled promise rejection.

This requirement applies only to `Modal.dialog`. The behavior of `Modal.confirm` and `Modal.alert` SHALL remain unchanged.

#### Scenario: Successful dialog submission reads fields and sends request

- **WHEN** a user enters a valid value in a dialog field and clicks the confirm button
- **THEN** `onConfirm` reads the dialog's input fields (which are still present in the DOM) and issues its request
- **AND** no unhandled promise rejection appears in the browser console
- **AND** on success the dialog closes (or the page navigates as the callback directs)

#### Scenario: Dialog stays open on validation failure

- **WHEN** a required dialog field is empty and the user clicks the confirm button
- **THEN** `onConfirm` returns `false`
- **AND** the dialog remains open with its entered field values preserved

#### Scenario: Dialog shows in-modal error and stays open on request failure

- **WHEN** the request issued by `onConfirm` fails
- **THEN** `onConfirm` writes an error message into the dialog's in-modal error element
- **AND** the dialog remains open so the error message is visible

#### Scenario: Dialog succeeds but stays open to show an in-modal message

- **WHEN** a dialog action succeeds but is designed to keep the dialog open (for example, joining a class shows an in-modal success message)
- **THEN** the success message is displayed inside the dialog
- **AND** the dialog remains open


<!-- @trace
source: fix-modal-confirm-lifecycle
updated: 2026-06-29
code:
  - src/templates/teacher/badges_manage.html
  - src/templates/student/dashboard.html
  - src/templates/shared/base.html
-->

---
### Requirement: Nested modals preserve the underlying modal content

The Modal component SHALL allow a modal to be opened from within another modal's callback without destroying the originating modal's content. Closing the topmost modal SHALL restore the underlying modal's content and state. A callback that opens a follow-up `Modal.alert` SHALL display that alert with its message and SHALL NOT overwrite or blank out a modal that remains open underneath.

#### Scenario: Revoking from a badge detail dialog keeps the detail visible

- **WHEN** a teacher confirms a revoke action triggered from inside the badge detail modal
- **THEN** the revoke is applied
- **AND** the badge detail modal content remains visible and consistent (it does not vanish or become blank)

#### Scenario: Follow-up alert from a confirm callback displays correctly

- **WHEN** a `Modal.confirm` callback opens a `Modal.alert` (for example, to report a failed action)
- **THEN** the alert is displayed with its message
- **AND** no modal content is overwritten or left blank

<!-- @trace
source: fix-modal-confirm-lifecycle
updated: 2026-06-29
code:
  - src/templates/teacher/badges_manage.html
  - src/templates/student/dashboard.html
  - src/templates/shared/base.html
-->