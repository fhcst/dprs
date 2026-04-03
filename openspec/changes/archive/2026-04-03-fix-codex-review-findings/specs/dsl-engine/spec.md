## MODIFIED Requirements

### Requirement: Dual compilation targets

The `dsl-engine` crate SHALL compile to two targets: WebAssembly (via `wasm-pack`) producing an npm package, and Python native binding (via `maturin` with PyO3) producing a Python wheel. Both targets SHALL expose the same API surface: `parse`, `validate`, `evaluate`, `complete`, `hover_info`, `describe`, and `get_help_content`. Both targets SHALL produce identical results for identical inputs. The Python wheel SHALL be declared as a project dependency so that `uv sync` installs it automatically. The Dockerfile SHALL include `maturin build` and wheel installation steps. If the `dsl_engine` module is not available at runtime, the `_validate_expression()` function SHALL raise a clear error message instead of an unhandled `ModuleNotFoundError`.

#### Scenario: WASM and PyO3 produce same parse result

- **WHEN** the same expression string is passed to `parse()` on both WASM and PyO3 targets
- **THEN** both SHALL return structurally identical AST or identical error messages

#### Scenario: WASM package importable in browser

- **WHEN** the WASM build completes
- **THEN** the output SHALL be a valid npm package importable via `import * as dsl from 'dsl-engine'`

#### Scenario: PyO3 wheel importable in Python

- **WHEN** the PyO3 build completes
- **THEN** the output SHALL be importable via `import dsl_engine` in Python 3.13+

#### Scenario: Graceful error when dsl_engine not installed

- **WHEN** the Python environment does not have the `dsl_engine` module installed and a teacher attempts to create a trigger rule
- **THEN** the system SHALL return a clear error message indicating the DSL engine is not available, NOT an unhandled 500 error
