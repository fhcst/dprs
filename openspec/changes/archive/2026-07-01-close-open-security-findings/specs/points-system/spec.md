## ADDED Requirements

### Requirement: Class-scoped point balance

The system SHALL provide a `get_class_balance(student_id, class_id)` operation that sums only the point transactions belonging to the given `(student_id, class_id)` pair. Class-facing surfaces that must not expose or draw on other classes' totals — notably the revoke cap — SHALL use the class-scoped balance rather than the global `get_balance()`. The `revoke_points()` operation SHALL cap the deduction at the student's class-scoped balance.

#### Scenario: Class-scoped balance excludes other classes

- **WHEN** a student has transactions in class A and class B
- **THEN** `get_class_balance(student, A)` SHALL return only class A's total, while `get_balance(student)` SHALL still return the combined total

#### Scenario: Revoke cap uses the class-scoped balance

- **WHEN** a teacher revokes points from a student in class A
- **THEN** the deduction SHALL be capped at the student's balance within class A and SHALL NOT be increased by points the student earned in another class

### Requirement: Points management page enforces class management

The teacher points-management page `GET /pages/classes/{class_id}/points` SHALL require `can_manage_class()` on the class before disclosing member balances, and SHALL display each student's class-scoped balance rather than their global balance. A teacher who does not manage the class SHALL receive HTTP 403.

#### Scenario: Non-managing teacher opens another class's points page

- **WHEN** a teacher who does not manage the class requests its points-management page
- **THEN** the system SHALL return HTTP 403 and SHALL NOT disclose member balances

#### Scenario: Points page shows class-scoped balances

- **WHEN** a managing teacher opens the points page for their class
- **THEN** each member's displayed balance SHALL reflect only that class's transactions
