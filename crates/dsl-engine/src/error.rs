use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Position in source code.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Span {
    pub start: usize,
    pub end: usize,
    pub line: usize,
    pub col: usize,
}

/// Parse error with location information.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParseError {
    pub message: String,
    pub span: Span,
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Parse error at line {}:{}: {}",
            self.span.line, self.span.col, self.message
        )
    }
}

/// Diagnostic severity levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Error,
    Warning,
}

/// Validation diagnostic with location and severity.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Diagnostic {
    pub message: String,
    pub severity: Severity,
    pub span: Option<Span>,
}

/// Evaluation error.
#[derive(Debug, Clone, Error, PartialEq, Serialize, Deserialize)]
pub enum EvalError {
    #[error("Missing variable in context: {0}")]
    MissingVariable(String),
    #[error("Type mismatch: expected {expected}, got {got}")]
    TypeMismatch { expected: String, got: String },
    #[error("Unknown function: {0}")]
    UnknownFunction(String),
    #[error("Invalid arguments for function {0}: {1}")]
    InvalidFuncArgs(String, String),
    #[error("Division by zero")]
    DivisionByZero,
}
