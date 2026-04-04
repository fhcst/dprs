## ADDED Requirements

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

### Requirement: Pre-release tag handling

For pre-release versions (containing a hyphen after the patch number, e.g., `1.0.0-rc1`), the script SHALL generate only the full pre-release tag. The script SHALL NOT generate expanded major/minor tags and SHALL NOT update `:latest`.

#### Scenario: Release candidate

- **WHEN** the detected version is `1.0.0-rc1`
- **THEN** the script SHALL generate only the tag `:1.0.0-rc1`

#### Scenario: Beta pre-release

- **WHEN** the detected version is `0.5.0-beta.2`
- **THEN** the script SHALL generate only the tag `:0.5.0-beta.2`

### Requirement: Commit hash fallback tag

When no git tag exists on the current commit, the script SHALL generate only a single tag using the short commit hash. The script SHALL NOT update `:latest`.

#### Scenario: No tag on HEAD

- **WHEN** no git tag exists on HEAD and the short hash is `abc1234`
- **THEN** the script SHALL generate only the tag `:sha-abc1234`

### Requirement: Cross-platform build and push

The script SHALL invoke `docker buildx build` with `--platform linux/amd64,linux/arm64` and `--push` to build and push multi-architecture images in a single step.

Each generated tag SHALL be passed as a separate `--tag` argument to the buildx command.

#### Scenario: Stable release build command

- **WHEN** the image name is `ghcr.io/fhcst/dprs` and the version is `1.2.3`
- **THEN** the script SHALL execute `docker buildx build --platform linux/amd64,linux/arm64 --push --tag ghcr.io/fhcst/dprs:1 --tag ghcr.io/fhcst/dprs:1.2 --tag ghcr.io/fhcst/dprs:1.2.3 --tag ghcr.io/fhcst/dprs:latest .`

#### Scenario: Commit hash build command

- **WHEN** the image name is `ghcr.io/fhcst/dprs` and there is no tag (hash `abc1234`)
- **THEN** the script SHALL execute `docker buildx build --platform linux/amd64,linux/arm64 --push --tag ghcr.io/fhcst/dprs:sha-abc1234 .`

### Requirement: Builder instance management

The script SHALL ensure a buildx builder instance capable of multi-platform builds exists. If no suitable builder is active, the script SHALL create one.

#### Scenario: No existing multi-platform builder

- **WHEN** no buildx builder with multi-platform support is active
- **THEN** the script SHALL create a builder instance and use it for the build

#### Scenario: Existing builder available

- **WHEN** a suitable buildx builder is already active
- **THEN** the script SHALL reuse the existing builder
