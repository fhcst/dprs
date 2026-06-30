# docker-buildx Specification

## Purpose

TBD - created by archiving change 'docker-buildx-script'. Update Purpose after archive.

## Requirements

### Requirement: Image name derivation from git remote

The script SHALL derive the Docker image name from the git remote `origin` URL by extracting the `<owner>/<repo>` portion and prepending `ghcr.io/`. The script SHALL support both HTTPS (`https://github.com/<owner>/<repo>.git`) and SSH (`git@github.com:<owner>/<repo>.git`) remote URL formats. The `.git` suffix SHALL be stripped if present.

The script SHALL accept an `--image` flag that overrides the derived image name.

#### Scenario: HTTPS remote URL

- **WHEN** the git remote origin is `https://github.com/fhcst/dprs.git`
- **THEN** the derived image name SHALL be `ghcr.io/fhcst/dprs`

#### Scenario: SSH remote URL

- **WHEN** the git remote origin is `git@github.com:fhcst/dprs.git`
- **THEN** the derived image name SHALL be `ghcr.io/fhcst/dprs`

#### Scenario: Override with --image flag

- **WHEN** the user passes `--image ghcr.io/other-org/other-name`
- **THEN** the script SHALL use `ghcr.io/other-org/other-name` as the image name, ignoring the git remote


<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: Version detection from git tags

The script SHALL detect the current version from git tags. The script SHALL use `git describe --tags --exact-match HEAD` to find a tag on the current commit. If no exact tag exists, the script SHALL fall back to the short commit hash (7 characters) prefixed with `sha-`.

#### Scenario: Current commit has a semver tag

- **WHEN** HEAD is tagged `v1.2.3`
- **THEN** the detected version SHALL be `1.2.3`

#### Scenario: Current commit has no tag

- **WHEN** HEAD has no tag and the short commit hash is `abc1234`
- **THEN** the detected version SHALL be `sha-abc1234`

#### Scenario: Tag without v prefix

- **WHEN** HEAD is tagged `1.2.3` (no `v` prefix)
- **THEN** the detected version SHALL be `1.2.3`


<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: Semver tag expansion for stable releases

For stable releases (no pre-release suffix), the script SHALL generate expanded tags based on the major version number.

When major version ≥ 1, the script SHALL generate: `:<major>`, `:<major>.<minor>`, `:<major>.<minor>.<patch>`, and `:latest`.

When major version = 0, the script SHALL skip the `:<major>` tag and generate: `:<major>.<minor>`, `:<major>.<minor>.<patch>`, and `:latest`.

#### Scenario: Stable release with major >= 1

- **WHEN** the detected version is `1.2.3`
- **THEN** the script SHALL generate tags: `:1`, `:1.2`, `:1.2.3`, `:latest`

#### Scenario: Stable release with major = 0

- **WHEN** the detected version is `0.3.1`
- **THEN** the script SHALL generate tags: `:0.3`, `:0.3.1`, `:latest`

#### Scenario: Stable release v2.0.0

- **WHEN** the detected version is `2.0.0`
- **THEN** the script SHALL generate tags: `:2`, `:2.0`, `:2.0.0`, `:latest`


<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: Pre-release tag handling

For pre-release versions (containing a hyphen after the patch number, e.g., `1.0.0-rc1`), the script SHALL generate only the full pre-release tag. The script SHALL NOT generate expanded major/minor tags and SHALL NOT update `:latest`.

#### Scenario: Release candidate

- **WHEN** the detected version is `1.0.0-rc1`
- **THEN** the script SHALL generate only the tag `:1.0.0-rc1`

#### Scenario: Beta pre-release

- **WHEN** the detected version is `0.5.0-beta.2`
- **THEN** the script SHALL generate only the tag `:0.5.0-beta.2`


<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: Commit hash fallback tag

When no git tag exists on the current commit, the script SHALL generate only a single tag using the short commit hash. The script SHALL NOT update `:latest`.

#### Scenario: No tag on HEAD

- **WHEN** no git tag exists on HEAD and the short hash is `abc1234`
- **THEN** the script SHALL generate only the tag `:sha-abc1234`


<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: Cross-platform build and push

The script SHALL invoke `docker buildx build` with `--platform linux/amd64,linux/arm64` and `--push` to build and push multi-architecture images in a single step. The Dockerfile SHALL be fully self-contained: the built image SHALL include both the PyO3 wheel and the WASM bundle without requiring any pre-built artifacts in the local build context.

Each generated tag SHALL be passed as a separate `--tag` argument to the buildx command.

#### Scenario: Stable release build command

- **WHEN** the image name is `ghcr.io/fhcst/dprs` and the version is `1.2.3`
- **THEN** the script SHALL execute `docker buildx build --platform linux/amd64,linux/arm64 --push --tag ghcr.io/fhcst/dprs:1 --tag ghcr.io/fhcst/dprs:1.2 --tag ghcr.io/fhcst/dprs:1.2.3 --tag ghcr.io/fhcst/dprs:latest .`

#### Scenario: Commit hash build command

- **WHEN** the image name is `ghcr.io/fhcst/dprs` and there is no tag (hash `abc1234`)
- **THEN** the script SHALL execute `docker buildx build --platform linux/amd64,linux/arm64 --push --tag ghcr.io/fhcst/dprs:sha-abc1234 .`

#### Scenario: No pre-built artifacts required

- **WHEN** `docker build` is executed on a machine with no Rust toolchain and no local `crates/dsl-engine/pkg/` artifacts
- **THEN** the build SHALL succeed and produce a fully functional image


<!-- @trace
source: docker-wasm-build-fix
updated: 2026-04-09
code:
  - src/templates/admin/users_list.html
  - src/templates/teacher/badges_manage.html
  - src/templates/teacher/class_hub.html
  - .agents/skills/spectra-ask
  - src/main.py
  - .agents/skills/spectra-apply
  - .agents/skills/spectra-archive
  - .agents/skills/spectra-discuss
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - src/pages/router.py
  - src/templates/student/badges.html
  - src/templates/teacher/points_manage.html
  - scripts/migrations/role_to_permissions.py
  - src/templates/setup.html
  - src/templates/shared/base.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/login.html
  - src/static/css/input.css
  - src/core/users/router.py
  - .agents/skills/spectra-audit
  - .agents/skills/spectra-debug
  - Dockerfile
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - .agents/skills/spectra-ingest
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - docs/uiux-audit/20260408/00-index.md
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/templates_list.html
  - src/templates/teacher/submission_review.html
  - src/templates/student/learning_history.html
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/community/feed.html
  - .agents/skills/spectra-propose
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - src/templates/community/leaderboard.html
  - src/templates/settings.html
  - src/templates/student/class_history.html
  - src/templates/student/dashboard.html
  - crates/dsl-engine/uv.lock
  - src/templates/shared/macros.html
tests:
  - tests/test_dashboard_and_page_bugs.py
  - tests/test_class_hub_page.py
  - tests/test_admin_users.py
  - tests/auth/test_role_migration.py
-->

---
### Requirement: Builder instance management

The script SHALL ensure a buildx builder instance capable of multi-platform builds exists. If no suitable builder is active, the script SHALL create one.

#### Scenario: No existing multi-platform builder

- **WHEN** no buildx builder with multi-platform support is active
- **THEN** the script SHALL create a builder instance and use it for the build

#### Scenario: Existing builder available

- **WHEN** a suitable buildx builder is already active
- **THEN** the script SHALL reuse the existing builder

<!-- @trace
source: docker-buildx-script
updated: 2026-04-04
code:
  - scripts/docker-build.sh
-->

---
### Requirement: WASM bundle built in Docker multi-stage build

The Dockerfile Stage 1 (`dsl-builder`) SHALL install `wasm-pack` and the `wasm32-unknown-unknown` Rust target in addition to the existing Rust toolchain and `maturin`. Stage 1 SHALL execute `wasm-pack build --target web --out-dir /wasm-pkg --release` after the PyO3 wheel build. Stage 2 SHALL copy the WASM bundle from the builder stage via `COPY --from=dsl-builder /wasm-pkg ./crates/dsl-engine/pkg` instead of copying from the local build context.

#### Scenario: Fresh clone Docker build produces functional WASM bundle

- **WHEN** `docker build` is executed after a fresh `git clone` (no local wasm-pack build performed)
- **THEN** the resulting Docker image SHALL contain a valid WASM bundle at `/app/crates/dsl-engine/pkg/` including `dsl_engine_bg.wasm` and `dsl_engine.js`
- **THEN** the FastAPI application SHALL mount these files at `/static/dsl-engine/`

#### Scenario: WASM bundle contents match wasm-pack output

- **WHEN** the Docker image is built
- **THEN** the `/app/crates/dsl-engine/pkg/dsl_engine.js` file SHALL be a valid ES module importable via `import()` in a browser
- **THEN** the `/app/crates/dsl-engine/pkg/dsl_engine_bg.wasm` file SHALL be a valid WebAssembly binary

<!-- @trace
source: docker-wasm-build-fix
updated: 2026-04-09
code:
  - src/templates/admin/users_list.html
  - src/templates/teacher/badges_manage.html
  - src/templates/teacher/class_hub.html
  - .agents/skills/spectra-ask
  - src/main.py
  - .agents/skills/spectra-apply
  - .agents/skills/spectra-archive
  - .agents/skills/spectra-discuss
  - src/templates/teacher/template_assign.html
  - docs/uiux-audit/20260408/01-accessibility.md
  - docs/uiux-audit/20260408/02-navigation-information-architecture.md
  - src/pages/router.py
  - src/templates/student/badges.html
  - src/templates/teacher/points_manage.html
  - scripts/migrations/role_to_permissions.py
  - src/templates/setup.html
  - src/templates/shared/base.html
  - src/templates/student/submit_task.html
  - docs/uiux-audit/20260408/07-content-empty-states.md
  - src/templates/login.html
  - src/static/css/input.css
  - src/core/users/router.py
  - .agents/skills/spectra-audit
  - .agents/skills/spectra-debug
  - Dockerfile
  - docs/uiux-audit/20260408/06-mobile-responsive-audit.md
  - .agents/skills/spectra-ingest
  - docs/uiux-audit/20260408/05-interaction-feedback-patterns.md
  - docs/uiux-audit/20260408/00-index.md
  - scripts/build-css.sh
  - src/templates/admin/user_form.html
  - src/templates/teacher/attendance_manage.html
  - src/templates/teacher/templates_list.html
  - src/templates/teacher/submission_review.html
  - src/templates/student/learning_history.html
  - docs/uiux-audit/20260408/03-role-workflow-analysis.md
  - docs/uiux-audit/20260408/04-design-system-consistency.md
  - src/templates/admin/classes_list.html
  - src/templates/community/feed.html
  - .agents/skills/spectra-propose
  - docs/uiux-audit/20260408/08-recommendations-roadmap.md
  - src/templates/community/leaderboard.html
  - src/templates/settings.html
  - src/templates/student/class_history.html
  - src/templates/student/dashboard.html
  - crates/dsl-engine/uv.lock
  - src/templates/shared/macros.html
tests:
  - tests/test_dashboard_and_page_bugs.py
  - tests/test_class_hub_page.py
  - tests/test_admin_users.py
  - tests/auth/test_role_migration.py
-->