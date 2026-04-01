use crate::ast::{CompareOp, Expr, FuncArg};
use crate::error::{Diagnostic, Severity};
use crate::types::{builtin_var_type, is_builtin_func, is_builtin_var};

/// Validate a DSL expression string, returning diagnostics.
pub fn validate(source: &str) -> Vec<Diagnostic> {
    let ast = match crate::parse(source) {
        Ok(ast) => ast,
        Err(errors) => {
            return errors
                .into_iter()
                .map(|e| Diagnostic {
                    message: e.message,
                    severity: Severity::Error,
                    span: Some(e.span),
                })
                .collect();
        }
    };

    let mut diagnostics = Vec::new();
    validate_expr(&ast, &mut diagnostics);
    diagnostics
}

fn validate_expr(expr: &Expr, diagnostics: &mut Vec<Diagnostic>) {
    match expr {
        Expr::Compare { left, op, right } => {
            validate_expr(left, diagnostics);
            validate_expr(right, diagnostics);
            check_type_compatibility(left, *op, right, diagnostics);
        }
        Expr::And(left, right) | Expr::Or(left, right) => {
            validate_expr(left, diagnostics);
            validate_expr(right, diagnostics);
        }
        Expr::Not(inner) => {
            validate_expr(inner, diagnostics);
        }
        Expr::Group(inner) => {
            validate_expr(inner, diagnostics);
        }
        Expr::Var(name) => {
            if !is_builtin_var(name) {
                diagnostics.push(Diagnostic {
                    message: format!("Undefined variable: `{}`", name),
                    severity: Severity::Error,
                    span: None,
                });
            }
        }
        Expr::FuncCall { name, args } => {
            if !is_builtin_func(name) {
                diagnostics.push(Diagnostic {
                    message: format!("Unknown function: `{}`", name),
                    severity: Severity::Error,
                    span: None,
                });
            } else {
                validate_func_args(name, args, diagnostics);
            }
        }
        // Literals are always valid
        Expr::IntLit(_) | Expr::FloatLit(_) | Expr::StringLit(_) | Expr::BoolLit(_) => {}
    }
}

fn validate_func_args(name: &str, args: &[FuncArg], diagnostics: &mut Vec<Diagnostic>) {
    match name {
        "count" => {
            if args.len() != 2 {
                diagnostics.push(Diagnostic {
                    message: format!(
                        "Function `count` expects 2 arguments, got {}",
                        args.len()
                    ),
                    severity: Severity::Error,
                    span: None,
                });
                return;
            }
            // First arg must be "submissions" or "checkins"
            match &args[0] {
                FuncArg::Ident(id) if id == "submissions" || id == "checkins" => {}
                _ => {
                    diagnostics.push(Diagnostic {
                        message: "First argument to `count` must be `submissions` or `checkins`"
                            .into(),
                        severity: Severity::Error,
                        span: None,
                    });
                }
            }
            // Second arg must be a time window
            match &args[1] {
                FuncArg::TimeWindow(_) => {}
                _ => {
                    diagnostics.push(Diagnostic {
                        message:
                            "Second argument to `count` must be a time window (e.g., `last_7_days`)"
                                .into(),
                        severity: Severity::Error,
                        span: None,
                    });
                }
            }
        }
        "day_of_week" => {
            if args.len() != 1 {
                diagnostics.push(Diagnostic {
                    message: format!(
                        "Function `day_of_week` expects 1 argument, got {}",
                        args.len()
                    ),
                    severity: Severity::Error,
                    span: None,
                });
                return;
            }
            // Argument must be a datetime variable (event.occurred_at)
            match &args[0] {
                FuncArg::Ident(id) if builtin_var_type(id) == Some("datetime") => {}
                FuncArg::Expr(expr) => match expr.as_ref() {
                    Expr::Var(v) if builtin_var_type(v) == Some("datetime") => {}
                    _ => {
                        diagnostics.push(Diagnostic {
                            message: "Argument to `day_of_week` must be a datetime variable"
                                .into(),
                            severity: Severity::Error,
                            span: None,
                        });
                    }
                },
                _ => {
                    diagnostics.push(Diagnostic {
                        message: "Argument to `day_of_week` must be a datetime variable".into(),
                        severity: Severity::Error,
                        span: None,
                    });
                }
            }
        }
        _ => {} // Unknown functions already caught above
    }
}

/// Infer the type of an expression for type-checking comparisons.
fn infer_type(expr: &Expr) -> Option<&'static str> {
    match expr {
        Expr::Var(name) => builtin_var_type(name),
        Expr::IntLit(_) => Some("int"),
        Expr::FloatLit(_) => Some("float"),
        Expr::StringLit(_) => Some("string"),
        Expr::BoolLit(_) => Some("bool"),
        Expr::FuncCall { name, .. } => match name.as_str() {
            "count" => Some("int"),
            "day_of_week" => Some("int"),
            _ => None,
        },
        _ => None,
    }
}

fn check_type_compatibility(
    left: &Expr,
    _op: CompareOp,
    right: &Expr,
    diagnostics: &mut Vec<Diagnostic>,
) {
    let left_type = infer_type(left);
    let right_type = infer_type(right);

    if let (Some(lt), Some(rt)) = (left_type, right_type) {
        // int and float are compatible
        let compatible = match (lt, rt) {
            (a, b) if a == b => true,
            ("int", "float") | ("float", "int") => true,
            _ => false,
        };
        if !compatible {
            diagnostics.push(Diagnostic {
                message: format!("Type mismatch: cannot compare {} with {}", lt, rt),
                severity: Severity::Error,
                span: None,
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_expression_no_diagnostics() {
        let diags = validate("checkin_streak >= 7 AND submission_count >= 3");
        assert!(diags.is_empty(), "Expected no diagnostics, got: {:?}", diags);
    }

    #[test]
    fn unknown_variable_error() {
        let diags = validate("unknown_var >= 5");
        assert_eq!(diags.len(), 1);
        assert_eq!(diags[0].severity, Severity::Error);
        assert!(diags[0].message.contains("unknown_var"));
    }

    #[test]
    fn type_mismatch_int_string() {
        let diags = validate("checkin_count == \"hello\"");
        assert_eq!(diags.len(), 1);
        assert!(diags[0].message.contains("Type mismatch"));
    }

    #[test]
    fn valid_function_no_error() {
        let diags = validate("count(submissions, last_7_days) >= 5");
        assert!(diags.is_empty(), "Expected no diagnostics, got: {:?}", diags);
    }

    #[test]
    fn unknown_function_error() {
        let diags = validate("unknown_func(submissions, last_7_days) >= 5");
        assert_eq!(diags.len(), 1);
        assert!(diags[0].message.contains("Unknown function"));
    }

    #[test]
    fn count_wrong_first_arg() {
        let diags = validate("count(badges, last_7_days) >= 5");
        assert!(!diags.is_empty());
        assert!(diags[0].message.contains("submissions"));
    }

    #[test]
    fn count_wrong_arg_count() {
        let diags = validate("count(submissions) >= 5");
        assert!(!diags.is_empty());
        assert!(diags[0].message.contains("2 arguments"));
    }

    #[test]
    fn valid_string_comparison() {
        let diags = validate("event.type == \"checkin\"");
        assert!(diags.is_empty());
    }

    #[test]
    fn invalid_syntax_returns_parse_error() {
        let diags = validate("checkin_streak >= AND 7");
        assert!(!diags.is_empty());
        assert_eq!(diags[0].severity, Severity::Error);
    }

    #[test]
    fn int_float_compatible() {
        let diags = validate("points >= 3.5");
        assert!(diags.is_empty());
    }
}
