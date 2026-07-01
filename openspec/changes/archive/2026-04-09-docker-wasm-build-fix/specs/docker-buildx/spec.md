## ADDED Requirements

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

## MODIFIED Requirements

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
