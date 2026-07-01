use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Values that DSL expressions can operate on.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Value {
    Int(i64),
    Float(f64),
    Bool(bool),
    String(String),
}

impl Value {
    pub fn type_name(&self) -> &'static str {
        match self {
            Value::Int(_) => "int",
            Value::Float(_) => "float",
            Value::Bool(_) => "bool",
            Value::String(_) => "string",
        }
    }
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::Int(v) => write!(f, "{}", v),
            Value::Float(v) => write!(f, "{}", v),
            Value::Bool(v) => write!(f, "{}", v),
            Value::String(v) => write!(f, "\"{}\"", v),
        }
    }
}

/// Context passed to the evaluator — pre-computed values for all built-in variables.
/// The service layer fills this from class-scoped MongoDB queries.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EvalContext {
    pub values: HashMap<String, Value>,
}

impl EvalContext {
    pub fn new() -> Self {
        Self {
            values: HashMap::new(),
        }
    }

    pub fn set(&mut self, key: impl Into<String>, value: Value) -> &mut Self {
        self.values.insert(key.into(), value);
        self
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.values.get(key)
    }
}

/// Built-in variable definition for validation and help.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuiltinVar {
    pub name: &'static str,
    pub var_type: &'static str,
    pub description_key: &'static str,
}

/// Built-in function definition for validation and help.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuiltinFunc {
    pub name: &'static str,
    pub signature: &'static str,
    pub return_type: &'static str,
    pub description_key: &'static str,
    pub example: &'static str,
}

/// The fixed set of built-in variables.
pub const BUILTIN_VARS: &[BuiltinVar] = &[
    BuiltinVar {
        name: "checkin_count",
        var_type: "int",
        description_key: "var.checkin_count",
    },
    BuiltinVar {
        name: "checkin_streak",
        var_type: "int",
        description_key: "var.checkin_streak",
    },
    BuiltinVar {
        name: "submission_count",
        var_type: "int",
        description_key: "var.submission_count",
    },
    BuiltinVar {
        name: "points",
        var_type: "int",
        description_key: "var.points",
    },
    BuiltinVar {
        name: "badge_count",
        var_type: "int",
        description_key: "var.badge_count",
    },
    BuiltinVar {
        name: "event.type",
        var_type: "string",
        description_key: "var.event_type",
    },
    BuiltinVar {
        name: "event.occurred_at",
        var_type: "datetime",
        description_key: "var.event_occurred_at",
    },
];

/// The fixed set of built-in functions.
pub const BUILTIN_FUNCS: &[BuiltinFunc] = &[
    BuiltinFunc {
        name: "count",
        signature: "count(submissions | checkins, last_N_days)",
        return_type: "int",
        description_key: "func.count",
        example: "count(submissions, last_7_days) >= 5",
    },
    BuiltinFunc {
        name: "day_of_week",
        signature: "day_of_week(datetime_expr)",
        return_type: "int",
        description_key: "func.day_of_week",
        example: "day_of_week(event.occurred_at) == 5",
    },
];

/// Check if a variable name is a known built-in.
pub fn is_builtin_var(name: &str) -> bool {
    BUILTIN_VARS.iter().any(|v| v.name == name)
}

/// Get the type of a built-in variable.
pub fn builtin_var_type(name: &str) -> Option<&'static str> {
    BUILTIN_VARS.iter().find(|v| v.name == name).map(|v| v.var_type)
}

/// Check if a function name is a known built-in.
pub fn is_builtin_func(name: &str) -> bool {
    BUILTIN_FUNCS.iter().any(|f| f.name == name)
}
