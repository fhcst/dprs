## ADDED Requirements

### Requirement: DSL expression parsing

The system SHALL provide a Rust crate `dsl-engine` that parses DSL expression strings into an AST. The parser SHALL accept comparison operators (`==`, `!=`, `>`, `>=`, `<`, `<=`), logical operators (`AND`, `OR`, `NOT`), grouping parentheses, numeric literals, string literals (double-quoted), boolean literals (`true`, `false`), and dot-notation variable access (e.g., `event.type`). The parser SHALL reject any syntax not defined in the grammar and return structured error messages with line and column positions.

#### Scenario: Valid expression parsed

- **WHEN** the parser receives `checkin_streak >= 7 AND submission_count >= 3`
- **THEN** the parser SHALL return a valid AST with a root AND node containing two comparison nodes

#### Scenario: Invalid syntax rejected

- **WHEN** the parser receives `checkin_streak >= AND 7`
- **THEN** the parser SHALL return an error with the position of the unexpected `AND` token

#### Scenario: Nested parentheses parsed

- **WHEN** the parser receives `(checkin_streak >= 7 OR badge_count >= 5) AND submission_count >= 3`
- **THEN** the parser SHALL return a valid AST respecting grouping precedence

### Requirement: DSL expression validation

The system SHALL validate parsed expressions against a fixed set of built-in variables and whitelisted functions. Built-in variables SHALL be: `checkin_count` (int), `checkin_streak` (int), `submission_count` (int), `points` (int), `badge_count` (int), `event.type` (string), `event.occurred_at` (datetime). Whitelisted functions SHALL be: `count(submissions, last_N_days)`, `count(checkins, last_N_days)`, `day_of_week(datetime_expr)`. The validator SHALL reject unknown variables, unknown functions, and type mismatches (e.g., comparing a string variable with a numeric literal).

#### Scenario: Unknown variable rejected

- **WHEN** the validator receives `unknown_var >= 5`
- **THEN** the validator SHALL return a diagnostic with severity "error" identifying `unknown_var` as undefined

#### Scenario: Type mismatch detected

- **WHEN** the validator receives `checkin_count == "hello"`
- **THEN** the validator SHALL return a diagnostic indicating type mismatch between int and string

#### Scenario: Valid function accepted

- **WHEN** the validator receives `count(submissions, last_7_days) >= 5`
- **THEN** the validator SHALL return zero error diagnostics

### Requirement: DSL expression evaluation

The system SHALL evaluate a validated DSL expression against an `EvalContext` containing pre-computed values for all built-in variables. The `evaluate()` function SHALL return `Result<bool, EvalError>`. The evaluator SHALL NOT perform any I/O, database queries, or network calls — it SHALL operate solely on the provided context values.

#### Scenario: Expression evaluates to true

- **WHEN** `evaluate("checkin_streak >= 7", {checkin_streak: 10})` is called
- **THEN** the function SHALL return `Ok(true)`

#### Scenario: Expression evaluates to false

- **WHEN** `evaluate("checkin_streak >= 7 AND submission_count >= 3", {checkin_streak: 10, submission_count: 1})` is called
- **THEN** the function SHALL return `Ok(false)`

#### Scenario: Missing context variable

- **WHEN** `evaluate("checkin_streak >= 7", {})` is called with an empty context
- **THEN** the function SHALL return `Err(EvalError)` indicating missing variable `checkin_streak`

### Requirement: DSL autocomplete suggestions

The system SHALL provide a `complete(source, cursor_pos)` function that returns contextually relevant suggestions. When the cursor is in a position expecting a variable, the function SHALL suggest all built-in variable names. When the cursor is after a comparison, the function SHALL suggest logical operators. When the cursor is in a function argument position, the function SHALL suggest valid argument values (e.g., `submissions`, `checkins`, `last_7_days`).

#### Scenario: Variable autocomplete

- **WHEN** `complete("check", 5)` is called
- **THEN** the function SHALL return suggestions including `checkin_count` and `checkin_streak`

#### Scenario: Operator autocomplete after value

- **WHEN** `complete("checkin_streak >= 7 ", 20)` is called
- **THEN** the function SHALL return suggestions including `AND`, `OR`

### Requirement: DSL hover information

The system SHALL provide a `hover_info(source, cursor_pos)` function that returns type and description metadata for the token at the given position. For built-in variables, it SHALL return the variable name, type, and a localized description. For functions, it SHALL return the function signature and description.

#### Scenario: Hover on variable

- **WHEN** `hover_info("checkin_streak >= 7", 5)` is called with the cursor on `checkin_streak`
- **THEN** the function SHALL return `{name: "checkin_streak", type: "int", description: "連續打卡天數"}`

### Requirement: DSL expression describe

The system SHALL provide a `describe(source, locale)` function that converts a valid DSL expression into a human-readable Markdown summary in the specified locale. For locale `tw`, the output SHALL be in Traditional Chinese. Each condition in the expression SHALL become a bullet point. AND-connected conditions SHALL be listed as separate bullets. OR-connected conditions SHALL be grouped with "或" separator.

#### Scenario: Simple condition described

- **WHEN** `describe("checkin_streak >= 7", "tw")` is called
- **THEN** the function SHALL return Markdown containing `連續打卡達 **7** 天`

#### Scenario: AND conditions described as bullet list

- **WHEN** `describe("checkin_streak >= 7 AND submission_count >= 3", "tw")` is called
- **THEN** the function SHALL return Markdown with two bullet points, one for each condition

### Requirement: DSL help content generation

The system SHALL provide a `get_help_content(locale)` function that returns a structured JSON object containing: all built-in variable names with types and descriptions, all operators with descriptions, all whitelisted functions with signatures and examples, and complete example expressions. The content SHALL be localized based on the `locale` parameter.

#### Scenario: Help content in Traditional Chinese

- **WHEN** `get_help_content("tw")` is called
- **THEN** the function SHALL return a JSON object with `variables`, `operators`, `functions`, and `examples` arrays, all descriptions in Traditional Chinese

### Requirement: Dual compilation targets

The `dsl-engine` crate SHALL compile to two targets: WebAssembly (via `wasm-pack`) producing an npm package, and Python native binding (via `maturin` with PyO3) producing a Python wheel. Both targets SHALL expose the same API surface: `parse`, `validate`, `evaluate`, `complete`, `hover_info`, `describe`, and `get_help_content`. Both targets SHALL produce identical results for identical inputs.

#### Scenario: WASM and PyO3 produce same parse result

- **WHEN** the same expression string is passed to `parse()` on both WASM and PyO3 targets
- **THEN** both SHALL return structurally identical AST or identical error messages

#### Scenario: WASM package importable in browser

- **WHEN** the WASM build completes
- **THEN** the output SHALL be a valid npm package importable via `import * as dsl from 'dsl-engine'`

#### Scenario: PyO3 wheel importable in Python

- **WHEN** the PyO3 build completes
- **THEN** the output SHALL be importable via `import dsl_engine` in Python 3.13+
