## ADDED Requirements

### Requirement: Project documentation reflects DSL engine and trigger-rule system

All OSS project documentation SHALL be updated to reflect the achievement DSL engine, trigger-rule management system, multi-stage Dockerfile, ClassMembership unique index, and associated security measures. Documentation updates SHALL cover README, CHANGELOG, CONTRIBUTING, SECURITY, architecture, extensions, and getting-started guides.

#### Scenario: Developer reads architecture docs after DSL feature merge

- **WHEN** a developer reads docs/architecture.md
- **THEN** the document SHALL include the Rust DSL engine integration, WASM/PyO3 dual-target architecture, and trigger-rule evaluation flow
