# docs-update Specification

## Purpose

TBD - created by archiving change 'update-oss-docs'. Update Purpose after archive.

## Requirements

### Requirement: Project documentation reflects DSL engine and trigger-rule system

All OSS project documentation SHALL be updated to reflect the achievement DSL engine, trigger-rule management system, multi-stage Dockerfile, ClassMembership unique index, and associated security measures. Documentation updates SHALL cover README, CHANGELOG, CONTRIBUTING, SECURITY, architecture, extensions, and getting-started guides.

#### Scenario: Developer reads architecture docs after DSL feature merge

- **WHEN** a developer reads docs/architecture.md
- **THEN** the document SHALL include the Rust DSL engine integration, WASM/PyO3 dual-target architecture, and trigger-rule evaluation flow

<!-- @trace
source: update-oss-docs
updated: 2026-04-03
code:
  - .agents/skills/spectra-ask
  - .agents/skills/spectra-ingest/SKILL.md
  - .agents/workflows/spectra-debug.md
  - .github/prompts/spectra-ask.prompt.md
  - .github/skills/spectra-audit/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-002.md
  - .agents/skills/spectra-propose/SKILL.md
  - GEMINI.md
  - .github/prompts/spectra-discuss.prompt.md
  - .agents/skills/spectra-audit
  - .github/prompts/spectra-audit.prompt.md
  - .agents/workflows/spectra-audit.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-005.md
  - .github/prompts/spectra-debug.prompt.md
  - .github/skills/spectra-discuss/SKILL.md
  - .agents/workflows/spectra-ask.md
  - .agents/skills
  - .agents/workflows/spectra-propose.md
  - .github/skills/spectra-propose/SKILL.md
  - .github/prompts/spectra-archive.prompt.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/workflows/spectra-archive.md
  - .agents/workflows/spectra-ingest.md
  - .github/skills/spectra-ask/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/tasks.md
  - .agents/skills/spectra-propose
  - .agents/workflows/spectra-apply.md
  - .codex/environments/environment.toml
  - .agents/skills/spectra-archive
  - .github/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - .agents/skills/spectra-discuss/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-003.md
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-001.md
  - .github/prompts/spectra-propose.prompt.md
  - .agents/skills/spectra-audit/SKILL.md
  - AGENTS.md
  - .agents/skills/spectra-ingest
  - .github/prompts/spectra-ingest.prompt.md
  - .security-audit/active/dprs-full-review-2026-04-02/plan.md
  - .agents/skills/spectra-discuss
  - .agents/skills/spectra-apply/SKILL.md
  - .github/skills/spectra-apply/SKILL.md
  - .agents/skills/spectra-apply
  - .agents/workflows/spectra-discuss.md
  - .github/prompts/spectra-apply.prompt.md
  - .github/skills/spectra-ingest/SKILL.md
  - .security-audit/active/dprs-full-review-2026-04-02/.audit.yaml
  - .security-audit/active/dprs-full-review-2026-04-02/findings/FINDING-004.md
  - .security-audit/active/dprs-full-review-2026-04-02/scope.md
  - .agents/workflows
  - .github/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug
-->