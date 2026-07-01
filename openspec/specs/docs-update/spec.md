# docs-update Specification

## Purpose

TBD - created by archiving change 'update-oss-docs'. Update Purpose after archive.

## Requirements

### Requirement: Project documentation reflects DSL engine and trigger-rule system

All OSS project documentation SHALL be updated to reflect the achievement DSL engine, trigger-rule management system, multi-stage Dockerfile, ClassMembership unique index, and associated security measures. Documentation updates SHALL cover README, CHANGELOG, CONTRIBUTING, SECURITY, architecture, extensions, and getting-started guides.

#### Scenario: Developer reads architecture docs after DSL feature merge

- **WHEN** a developer reads docs/architecture.md
- **THEN** the document SHALL include the Rust DSL engine integration, WASM/PyO3 dual-target architecture, and trigger-rule evaluation flow

### Requirement: Package version numbers are consistent at 1.0.0

All version identifiers across package metadata files SHALL be updated to `1.0.0` before the v1.0.0 release. Affected files: `pyproject.toml`, `crates/dsl-engine/Cargo.toml`, `crates/dsl-engine/pyproject.toml`.

#### Scenario: Developer checks version after update

- **WHEN** a developer reads `pyproject.toml`
- **THEN** the `version` field SHALL be `"1.0.0"`

#### Scenario: DSL Engine crate version matches main project

- **WHEN** a developer reads `crates/dsl-engine/Cargo.toml`
- **THEN** the `version` field SHALL be `"1.0.0"`, consistent with the root `pyproject.toml`

### Requirement: README follows OSS project conventions

The project `README.md` SHALL be restructured to match standard OSS project conventions, suitable for display as the primary GitHub repository page.

Required elements:
- `banner.png` image at the top of the file
- A badge strip with at minimum: CI status, license, and version badges
- A concise one-sentence project description
- A feature overview section (bullet list or concise table)
- A Quick Start section covering only the Docker Compose path
- A Documentation index table linking to all docs
- Contributing, Security, and License footer sections
- Inline environment variable details SHALL be removed and replaced with a link to `docs/configuration.md`

#### Scenario: New contributor views repository on GitHub

- **WHEN** a new contributor opens the GitHub repository page
- **THEN** they SHALL see the banner image at the top, followed by badge strip, project description, and a Quick Start that allows them to run the system with three commands or fewer

#### Scenario: README does not duplicate configuration details

- **WHEN** a reader looks for environment variable details in README
- **THEN** README SHALL link to `docs/configuration.md` rather than listing all variables inline

### Requirement: Teacher workflow documentation is UI-centric and current

`docs/user-guide/teacher-workflow.md` SHALL describe teacher actions through the web interface only. API reference tables SHALL be removed. Two new sections SHALL be added:

1. A "DSL 觸發規則管理" section covering: accessing the trigger-rules page, writing DSL expressions in the CodeMirror editor, using autocomplete and hover hints, running a dry-run test, and saving a rule.
2. An updated "徽章管理" section covering: the badge Detail Modal (viewing awarded/not-awarded students), performing a Soft Delete Revoke, and navigating via the badges sidebar link.

#### Scenario: Teacher reads workflow doc to learn DSL trigger rules

- **WHEN** a teacher reads the teacher workflow documentation
- **THEN** they SHALL find step-by-step instructions for creating and testing a DSL trigger rule without needing to consult the API documentation

#### Scenario: API reference tables are removed

- **WHEN** a reader opens `docs/user-guide/teacher-workflow.md`
- **THEN** the document SHALL NOT contain any `POST /classes/{class_id}/...` or similar API endpoint tables

### Requirement: Architecture document reflects v1.0.0 and DSL Engine

`docs/architecture.md` SHALL be updated so that:
- The version in the document header reflects `v1.0.0`
- The architecture diagram includes the DSL Engine subsystem (Rust/WASM/PyO3) and the Triggers module
- The module listing includes `src/gamification/triggers/`

#### Scenario: Developer reads architecture doc to understand DSL integration

- **WHEN** a developer reads `docs/architecture.md`
- **THEN** the document SHALL include a description of the DSL Engine (Rust crate, WASM front-end target, PyO3 Python binding target) and its position in the system architecture

### Requirement: Student workflow documents dedicated badges page

`docs/user-guide/student-workflow.md` Section 8 SHALL clarify that the badge collection is accessible as a standalone page at `/pages/students/me/badges`, not only as a strip on the Dashboard.

#### Scenario: Student wants to view all their badges

- **WHEN** a student reads the student workflow documentation
- **THEN** they SHALL find instructions for navigating to the dedicated badges page

### Requirement: Getting-started documents Docker Buildx multi-arch build

`docs/getting-started.md` SHALL include a section describing how to build multi-architecture Docker images using `scripts/docker-build.sh`, covering the `linux/amd64` and `linux/arm64` targets.

#### Scenario: Operator builds image for ARM server

- **WHEN** an operator reads the getting-started guide
- **THEN** they SHALL find instructions for running `scripts/docker-build.sh` to produce a multi-platform image

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