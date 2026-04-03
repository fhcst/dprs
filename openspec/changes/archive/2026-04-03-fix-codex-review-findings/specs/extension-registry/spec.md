## MODIFIED Requirements

### Requirement: FastAPI dependency injection via registry

The system SHALL provide FastAPI `Depends` factory functions that retrieve implementations from the registry. Routers and services SHALL use these factories rather than importing implementations directly. The `get_reward_providers()` function SHALL return a `list` of implementation objects (not a dict), so that callers can iterate providers directly with `for provider in get_reward_providers()`.

#### Scenario: Router uses injected provider

- **WHEN** a router endpoint declares a dependency on `get_reward_provider()`
- **THEN** FastAPI SHALL inject the registered RewardProvider for that event type

#### Scenario: Reward providers iterated as list

- **WHEN** a caller iterates `get_reward_providers()`
- **THEN** each element SHALL be a RewardProvider implementation object, NOT a dict key string
