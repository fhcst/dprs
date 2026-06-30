# prize-redemption Specification

## Purpose

TBD - created by archiving change 'add-prize-redemption'. Update Purpose after archive.

## Requirements

### Requirement: Student redeems a prize with sufficient points

The system SHALL provide an endpoint `POST /classes/{class_id}/prizes/{prize_id}/redeem` that lets the authenticated student redeem a prize. The redeemer SHALL be the student resolved from the request JWT. The system SHALL load the prize by `prize_id`, and SHALL only proceed when ALL of the following hold: the prize exists, `prize.class_id` equals the path `class_id`, the prize is visible, the student is a member of the class, and the student's point balance is greater than or equal to the prize's `point_cost`. On success, the system SHALL deduct exactly `point_cost` points and SHALL return the redemption result together with the student's recomputed balance.

#### Scenario: Successful redemption deducts the prize cost

- **WHEN** a class-member student with a balance of at least the prize's `point_cost` redeems a visible prize belonging to that class
- **THEN** the system SHALL deduct exactly `point_cost` points, return HTTP 2xx with the redemption result, and report a new balance equal to the previous balance minus `point_cost`

##### Example: balance drops by point_cost

- **GIVEN** student balance = 100 and prize `point_cost` = 30
- **WHEN** the student redeems the prize
- **THEN** the response reports `new_balance` = 70 and exactly one new negative ledger entry of amount -30 exists

---
### Requirement: Redemption is rejected when the balance is insufficient

When the student's point balance is less than the prize's `point_cost`, the system SHALL reject the redemption with a 4xx insufficient-points error and SHALL NOT create any point transaction.

#### Scenario: Insufficient balance is rejected without deduction

- **WHEN** a class-member student whose balance is less than the prize's `point_cost` attempts to redeem
- **THEN** the system SHALL return a 4xx insufficient-points error and the student's transaction count and balance SHALL remain unchanged

##### Example: redemption blocked, ledger unchanged

- **GIVEN** student balance = 20 and prize `point_cost` = 50
- **WHEN** the student attempts to redeem
- **THEN** the response is a 4xx insufficient-points error and the balance remains 20 with no new ledger entry

---
### Requirement: Redemption is restricted to class members

The system SHALL verify that the redeeming student is a member of the class identified by `prize.class_id` before allowing redemption. A non-member SHALL be rejected with HTTP 403 and no point transaction SHALL be created.

#### Scenario: Non-member cannot redeem

- **WHEN** a student who is not a member of the prize's class attempts to redeem a prize in that class
- **THEN** the system SHALL return HTTP 403 and SHALL NOT create any point transaction

---
### Requirement: Redemption is rejected for an invisible or cross-class prize

The system SHALL reject redemption when the prize is not visible, or when `prize.class_id` does not equal the path `class_id`. In both cases the system SHALL return a 4xx error and SHALL NOT create any point transaction. The system MUST derive the prize's class from the loaded prize record rather than trusting the caller-supplied `class_id`.

#### Scenario: Invisible prize cannot be redeemed

- **WHEN** a class-member student attempts to redeem a prize whose `visible` flag is false
- **THEN** the system SHALL reject the request with a 4xx error and SHALL NOT create any point transaction

#### Scenario: Prize from another class cannot be redeemed via mismatched path

- **WHEN** a student calls the redeem endpoint with a `class_id` that does not match the loaded prize's `class_id`
- **THEN** the system SHALL reject the request with a 4xx error and SHALL NOT create any point transaction

---
### Requirement: Redemption is recorded as a single point-ledger transaction

The system SHALL record a successful redemption by inserting exactly one `PointTransaction` with `amount` equal to the negative of `point_cost`, `source_event` equal to `"prize_redemption"`, `source_id` equal to the `prize_id`, `class_id` equal to the prize's `class_id`, and `created_by` equal to the redeeming student's id. The ledger entry SHALL be the redemption record; the system SHALL NOT introduce a separate redemption collection. The student's balance SHALL always be recomputed as the sum of all their transactions.

#### Scenario: One negative transaction captures the redemption

- **WHEN** a redemption succeeds for a prize with `point_cost` of 30
- **THEN** the system SHALL insert exactly one `PointTransaction` with `amount` = -30, `source_event` = "prize_redemption", and `source_id` = the prize id

---
### Requirement: Concurrent redemption re-checks balance before deduction

Immediately before inserting the deduction transaction, the system SHALL re-check the student's current balance against `point_cost` and SHALL abort without inserting when the balance is insufficient. The system SHALL NOT require multi-document transactions; because the deployment uses a standalone MongoDB instance, a residual time-of-check-to-time-of-use (TOCTOU) window remains and SHALL be treated as an accepted limitation consistent with the existing point ledger. The student-facing redeem control SHALL be disabled while a redemption request is in flight.

#### Scenario: Balance is re-checked immediately before insert

- **WHEN** the redeem service is about to insert the deduction transaction
- **THEN** the system SHALL re-read the current balance and SHALL abort the insert if the balance is now less than `point_cost`

---
### Requirement: Student prize redemption page

The system SHALL serve a student-facing prize page at `GET /pages/classes/{class_id}/prizes`. The page SHALL list the class's visible prizes with their `point_cost`, SHALL display the student's current point balance, and SHALL provide a redeem control per prize that opens a confirmation using the shared Modal, posts to the redeem endpoint, and reflects the new balance and redemption result in place. The redeem control SHALL be disabled while its request is in flight.

#### Scenario: Student views visible prizes and balance

- **WHEN** a student opens `GET /pages/classes/{class_id}/prizes` for a class they belong to
- **THEN** the system SHALL render an HTML page listing only the visible prizes for that class with their point costs and the student's current balance

#### Scenario: Redeeming from the page updates the balance in place

- **WHEN** the student confirms redemption of a prize from the page and the redemption succeeds
- **THEN** the page SHALL post to the redeem endpoint and update the displayed balance and the prize's redemption result without a full page reload
