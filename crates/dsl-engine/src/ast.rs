use serde::{Deserialize, Serialize};

/// The root AST node — a DSL expression evaluates to a boolean.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Expr {
    /// Binary comparison: left op right
    Compare {
        left: Box<Expr>,
        op: CompareOp,
        right: Box<Expr>,
    },
    /// Logical AND
    And(Box<Expr>, Box<Expr>),
    /// Logical OR
    Or(Box<Expr>, Box<Expr>),
    /// Logical NOT
    Not(Box<Expr>),
    /// Parenthesized grouping
    Group(Box<Expr>),
    /// Variable reference (e.g., `checkin_streak`, `event.type`)
    Var(String),
    /// Integer literal
    IntLit(i64),
    /// Float literal
    FloatLit(f64),
    /// String literal
    StringLit(String),
    /// Boolean literal
    BoolLit(bool),
    /// Function call: name(args...)
    FuncCall {
        name: String,
        args: Vec<FuncArg>,
    },
}

/// Comparison operators.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CompareOp {
    Eq,  // ==
    Ne,  // !=
    Gt,  // >
    Ge,  // >=
    Lt,  // <
    Le,  // <=
}

impl CompareOp {
    pub fn as_str(&self) -> &'static str {
        match self {
            CompareOp::Eq => "==",
            CompareOp::Ne => "!=",
            CompareOp::Gt => ">",
            CompareOp::Ge => ">=",
            CompareOp::Lt => "<",
            CompareOp::Le => "<=",
        }
    }
}

impl std::fmt::Display for CompareOp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// Function arguments — can be identifiers or special tokens like `last_N_days`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum FuncArg {
    /// A bare identifier like `submissions`, `checkins`
    Ident(String),
    /// A time window token like `last_7_days`
    TimeWindow(u32),
    /// An expression (e.g., variable reference)
    Expr(Box<Expr>),
}
