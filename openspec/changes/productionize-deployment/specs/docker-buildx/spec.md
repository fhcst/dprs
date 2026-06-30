## ADDED Requirements

### Requirement: GHCR image as the default compose run path

The `docker-compose.yml` default `app` service SHALL use `image: ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}` so that a plain `docker compose up` pulls the prebuilt image from GHCR. The local build SHALL be moved into an opt-in profile: a second service `app-build` under `profiles: [build]` SHALL declare `build: .` and the SAME `image:` tag as `app`, so that a locally built image is tagged identically to the GHCR image. Shared `app` configuration (environment, `depends_on`, restart policy) SHALL be reused via a YAML anchor to avoid duplication.

The `APP_IMAGE_TAG` value SHALL be supplied from the environment and default to `latest`.

#### Scenario: Default compose pulls the prebuilt image

- **WHEN** the operator runs `docker compose up` with no profile
- **THEN** the `app` service SHALL use image `ghcr.io/fhcst/dprs:latest` (or the value of `APP_IMAGE_TAG`)
- **THEN** compose SHALL pull the prebuilt image rather than building locally

#### Scenario: Build profile produces an identically tagged image

- **WHEN** the operator runs `docker compose --profile build build`
- **THEN** the `app-build` service SHALL build from `.`
- **THEN** the resulting local image SHALL carry the same `ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}` tag as the default `app` service

#### Scenario: Bootstrapping before the first publish

- **WHEN** no image has yet been published to GHCR
- **THEN** `docker compose up` SHALL be unable to pull `ghcr.io/fhcst/dprs:latest`
- **THEN** the documentation SHALL instruct the operator to run `docker compose --profile build build` first to produce the image locally

### Requirement: GitHub Actions publishes the multi-arch image on version tags

A GitHub Actions workflow (e.g. `.github/workflows/publish-image.yml`) SHALL build and push the multi-architecture image to `ghcr.io/fhcst/dprs` on push of a version tag (`v*`). A single trigger source (tag push) SHALL be used so the same version is not built and pushed twice, and a `concurrency` group SHALL prevent concurrent runs for the same ref. The workflow SHALL use `docker/setup-qemu-action`, `docker/setup-buildx-action`, `docker/login-action` (registry `ghcr.io`, username `${{ github.actor }}`, password `${{ secrets.GITHUB_TOKEN }}`), and `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`. The image tags SHALL be derived from the git tag, mirroring `scripts/docker-build.sh` (`v1.2.3` → `:1`, `:1.2`, `:1.2.3`, `:latest`; pre-release tags SHALL NOT expand shorthand tags and SHALL NOT update `:latest`). The workflow SHALL set `permissions: contents: read, packages: write` and SHALL NOT hardcode any secret.

#### Scenario: Stable version tag triggers a multi-arch publish

- **WHEN** a git tag `v1.2.3` is pushed
- **THEN** the workflow SHALL build for `linux/amd64,linux/arm64` and push to `ghcr.io/fhcst/dprs`
- **THEN** the pushed tags SHALL be `:1`, `:1.2`, `:1.2.3`, and `:latest`, mirroring `scripts/docker-build.sh`

#### Scenario: Pre-release tag does not update latest

- **WHEN** a git tag `v1.0.0-rc1` is pushed
- **THEN** the workflow SHALL push only the `:1.0.0-rc1` tag
- **THEN** the workflow SHALL NOT push expanded shorthand tags and SHALL NOT update `:latest`

#### Scenario: Authentication uses GITHUB_TOKEN without hardcoded secrets

- **WHEN** the workflow logs in to `ghcr.io`
- **THEN** it SHALL authenticate as `${{ github.actor }}` using `${{ secrets.GITHUB_TOKEN }}`
- **THEN** no secret value SHALL be hardcoded in the workflow, and `permissions` SHALL be `contents: read, packages: write`
