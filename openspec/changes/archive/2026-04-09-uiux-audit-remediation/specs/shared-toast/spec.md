## ADDED Requirements

### Requirement: Global toast notification container

The base template SHALL include a fixed-position toast notification container that is present on every page. The container SHALL have `role="status"` and `aria-live="polite"`.

#### Scenario: Any page loads

- **WHEN** any authenticated page loads
- **THEN** a toast container element SHALL exist in the DOM at `position: fixed`, top-right corner, with `z-index: 50`
- **THEN** the container SHALL have `role="status"` and `aria-live="polite"`

### Requirement: Toast API with three variants

The system SHALL provide a global JavaScript API with three toast variants: `Toast.success(message)`, `Toast.error(message)`, and `Toast.info(message)`. Each variant SHALL have distinct visual styling (green for success, red for error, blue for info).

#### Scenario: Success toast is triggered

- **WHEN** `Toast.success("任務提交成功")` is called
- **THEN** a toast element with green styling and a checkmark icon SHALL appear in the container
- **THEN** the toast SHALL auto-dismiss after 3 seconds

#### Scenario: Error toast is triggered

- **WHEN** `Toast.error("操作失敗")` is called
- **THEN** a toast element with red styling and a warning icon SHALL appear
- **THEN** the toast SHALL auto-dismiss after 5 seconds
- **THEN** the toast SHALL include a manual close button

#### Scenario: Info toast is triggered

- **WHEN** `Toast.info("已複製到剪貼簿")` is called
- **THEN** a toast element with blue styling and an info icon SHALL appear
- **THEN** the toast SHALL auto-dismiss after 3 seconds

### Requirement: Toast stacking

Multiple simultaneous toasts SHALL stack vertically with consistent spacing. Newer toasts SHALL appear below existing ones.

#### Scenario: Two toasts are triggered in quick succession

- **WHEN** `Toast.success("A")` and `Toast.info("B")` are called within 100ms of each other
- **THEN** both toasts SHALL be visible simultaneously, stacked vertically with spacing
