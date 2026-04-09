## ADDED Requirements

### Requirement: Modal ARIA dialog semantics

All modal dialogs SHALL have `role="dialog"` and `aria-modal="true"`. Each modal SHALL have `aria-labelledby` pointing to the modal's title element. Confirmation dialogs SHALL use `role="alertdialog"`.

#### Scenario: Create class modal opens

- **WHEN** the "Create class" modal opens
- **THEN** the modal container SHALL have `role="dialog"` and `aria-modal="true"`
- **THEN** the modal SHALL have `aria-labelledby` referencing the "新增班級" heading

### Requirement: Modal focus trap

When a modal is open, keyboard focus SHALL be trapped within the modal. Pressing Tab on the last focusable element SHALL cycle to the first focusable element. Pressing Shift+Tab on the first focusable element SHALL cycle to the last.

#### Scenario: User tabs through modal elements

- **WHEN** a modal is open and the user presses Tab on the last focusable element in the modal
- **THEN** focus SHALL move to the first focusable element in the modal

#### Scenario: User shift-tabs from first modal element

- **WHEN** a modal is open and the user presses Shift+Tab on the first focusable element
- **THEN** focus SHALL move to the last focusable element in the modal

### Requirement: Modal ESC key dismissal

All modals SHALL close when the user presses the Escape key.

#### Scenario: User presses Escape while modal is open

- **WHEN** a modal is open and the user presses the Escape key
- **THEN** the modal SHALL close
- **THEN** focus SHALL return to the element that triggered the modal

### Requirement: Modal focus restoration

When a modal closes, keyboard focus SHALL return to the element that originally triggered the modal opening.

#### Scenario: User closes modal via button

- **WHEN** a user opens a modal by clicking a trigger button and then closes the modal
- **THEN** focus SHALL return to the trigger button

### Requirement: Modal background scroll lock

When a modal is open, the page background SHALL NOT be scrollable.

#### Scenario: Modal is open on a long page

- **WHEN** a modal is open on a page with scrollable content
- **THEN** the background page SHALL NOT scroll when the user attempts to scroll

### Requirement: Modal mobile bottom sheet variant

On viewports narrower than 640px, modals with form content SHALL render as bottom sheets (anchored to the bottom of the viewport with top border radius) instead of centered overlays. The bottom sheet SHALL have `max-height: 85vh` and `overflow-y: auto`.

#### Scenario: Modal opens on mobile device

- **WHEN** a modal opens on a viewport narrower than 640px
- **THEN** the modal SHALL anchor to the bottom of the viewport
- **THEN** the modal SHALL have a maximum height of 85% of the viewport height
- **THEN** the modal content SHALL be scrollable if it exceeds the maximum height
