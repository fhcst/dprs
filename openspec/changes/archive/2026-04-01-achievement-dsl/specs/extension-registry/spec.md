## MODIFIED Requirements

### Requirement: Protocol definitions for extension points

The system SHALL define four Python Protocols in `src/extensions/protocols/`: `AuthProvider`, `RewardProvider`, `BadgeTrigger`, and `SubmissionValidator`. Each Protocol SHALL specify the exact method signatures that implementors MUST satisfy. The BadgeTrigger Protocol SHALL coexist with the DSL trigger rule system — badges SHALL use either a code-registered trigger (`trigger_key`) or a DSL rule (`trigger_rule_id`), but NOT both. The `evaluate_triggers_for_event()` function SHALL evaluate both code triggers and DSL rules in a single pass.

#### Scenario: Protocol checked at registration

- **WHEN** an implementation is registered that does not satisfy the Protocol interface
- **THEN** the ExtensionRegistry SHALL raise a TypeError at registration time

#### Scenario: Custom trigger registered

- **WHEN** a custom BadgeTrigger is registered in the ExtensionRegistry at startup
- **THEN** the system SHALL evaluate it after every reward event alongside built-in triggers and DSL rules

#### Scenario: Code trigger and DSL rule evaluated in same pass

- **WHEN** a reward event occurs and class C has badges bound to both code triggers and DSL rules
- **THEN** `evaluate_triggers_for_event()` SHALL evaluate both types and award badges for all matching conditions
