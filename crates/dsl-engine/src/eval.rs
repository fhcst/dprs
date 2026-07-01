use crate::ast::{CompareOp, Expr, FuncArg};
use crate::error::EvalError;
use crate::types::{EvalContext, Value};

/// Evaluate a DSL expression against a context, returning a boolean result.
/// Performs no I/O — operates solely on provided context values.
pub fn evaluate(source: &str, context: &EvalContext) -> Result<bool, EvalError> {
    let ast = crate::parse(source).map_err(|errors| {
        EvalError::TypeMismatch {
            expected: "valid expression".into(),
            got: errors
                .first()
                .map(|e| e.message.clone())
                .unwrap_or_default(),
        }
    })?;

    let result = eval_expr(&ast, context)?;
    to_bool(&result)
}

fn eval_expr(expr: &Expr, ctx: &EvalContext) -> Result<Value, EvalError> {
    match expr {
        Expr::Compare { left, op, right } => {
            let lval = eval_expr(left, ctx)?;
            let rval = eval_expr(right, ctx)?;
            Ok(Value::Bool(compare_values(&lval, *op, &rval)?))
        }
        Expr::And(left, right) => {
            let lval = eval_expr(left, ctx)?;
            let lb = to_bool(&lval)?;
            if !lb {
                return Ok(Value::Bool(false)); // short-circuit
            }
            let rval = eval_expr(right, ctx)?;
            Ok(Value::Bool(to_bool(&rval)?))
        }
        Expr::Or(left, right) => {
            let lval = eval_expr(left, ctx)?;
            let lb = to_bool(&lval)?;
            if lb {
                return Ok(Value::Bool(true)); // short-circuit
            }
            let rval = eval_expr(right, ctx)?;
            Ok(Value::Bool(to_bool(&rval)?))
        }
        Expr::Not(inner) => {
            let val = eval_expr(inner, ctx)?;
            Ok(Value::Bool(!to_bool(&val)?))
        }
        Expr::Group(inner) => eval_expr(inner, ctx),
        Expr::Var(name) => ctx
            .get(name)
            .cloned()
            .ok_or_else(|| EvalError::MissingVariable(name.clone())),
        Expr::IntLit(v) => Ok(Value::Int(*v)),
        Expr::FloatLit(v) => Ok(Value::Float(*v)),
        Expr::StringLit(v) => Ok(Value::String(v.clone())),
        Expr::BoolLit(v) => Ok(Value::Bool(*v)),
        Expr::FuncCall { name, args } => eval_func(name, args, ctx),
    }
}

fn eval_func(name: &str, args: &[FuncArg], ctx: &EvalContext) -> Result<Value, EvalError> {
    match name {
        "count" => {
            // count(submissions|checkins, last_N_days)
            // The context should have pre-computed values like "submissions_last_7_days"
            let source_name = match &args[0] {
                FuncArg::Ident(id) => id.clone(),
                _ => {
                    return Err(EvalError::InvalidFuncArgs(
                        "count".into(),
                        "first arg must be submissions or checkins".into(),
                    ))
                }
            };
            let days = match &args[1] {
                FuncArg::TimeWindow(n) => *n,
                _ => {
                    return Err(EvalError::InvalidFuncArgs(
                        "count".into(),
                        "second arg must be a time window".into(),
                    ))
                }
            };
            // Look up pre-computed key like "submissions_last_7_days"
            let key = format!("{}_last_{}_days", source_name, days);
            ctx.get(&key)
                .cloned()
                .ok_or_else(|| EvalError::MissingVariable(key))
        }
        "day_of_week" => {
            // day_of_week(event.occurred_at)
            // Context should have pre-computed "event.occurred_at.day_of_week"
            let var_name = match &args[0] {
                FuncArg::Ident(id) => format!("{}.day_of_week", id),
                FuncArg::Expr(expr) => match expr.as_ref() {
                    Expr::Var(v) => format!("{}.day_of_week", v),
                    _ => {
                        return Err(EvalError::InvalidFuncArgs(
                            "day_of_week".into(),
                            "argument must be a datetime variable".into(),
                        ))
                    }
                },
                _ => {
                    return Err(EvalError::InvalidFuncArgs(
                        "day_of_week".into(),
                        "argument must be a datetime variable".into(),
                    ))
                }
            };
            ctx.get(&var_name)
                .cloned()
                .ok_or_else(|| EvalError::MissingVariable(var_name))
        }
        _ => Err(EvalError::UnknownFunction(name.to_string())),
    }
}

fn to_bool(value: &Value) -> Result<bool, EvalError> {
    match value {
        Value::Bool(b) => Ok(*b),
        other => Err(EvalError::TypeMismatch {
            expected: "bool".into(),
            got: other.type_name().into(),
        }),
    }
}

fn compare_values(left: &Value, op: CompareOp, right: &Value) -> Result<bool, EvalError> {
    match (left, right) {
        (Value::Int(a), Value::Int(b)) => Ok(compare_ord(*a, op, *b)),
        (Value::Float(a), Value::Float(b)) => Ok(compare_float(*a, op, *b)),
        (Value::Int(a), Value::Float(b)) => Ok(compare_float(*a as f64, op, *b)),
        (Value::Float(a), Value::Int(b)) => Ok(compare_float(*a, op, *b as f64)),
        (Value::String(a), Value::String(b)) => Ok(compare_ord(a, op, b)),
        (Value::Bool(a), Value::Bool(b)) => match op {
            CompareOp::Eq => Ok(a == b),
            CompareOp::Ne => Ok(a != b),
            _ => Err(EvalError::TypeMismatch {
                expected: "comparable types".into(),
                got: "bool (only == and != supported)".into(),
            }),
        },
        _ => Err(EvalError::TypeMismatch {
            expected: left.type_name().into(),
            got: right.type_name().into(),
        }),
    }
}

fn compare_ord<T: Ord>(a: T, op: CompareOp, b: T) -> bool {
    match op {
        CompareOp::Eq => a == b,
        CompareOp::Ne => a != b,
        CompareOp::Gt => a > b,
        CompareOp::Ge => a >= b,
        CompareOp::Lt => a < b,
        CompareOp::Le => a <= b,
    }
}

fn compare_float(a: f64, op: CompareOp, b: f64) -> bool {
    match op {
        CompareOp::Eq => (a - b).abs() < f64::EPSILON,
        CompareOp::Ne => (a - b).abs() >= f64::EPSILON,
        CompareOp::Gt => a > b,
        CompareOp::Ge => a >= b,
        CompareOp::Lt => a < b,
        CompareOp::Le => a <= b,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ctx_with(pairs: &[(&str, Value)]) -> EvalContext {
        let mut ctx = EvalContext::new();
        for (k, v) in pairs {
            ctx.set(*k, v.clone());
        }
        ctx
    }

    #[test]
    fn eval_simple_true() {
        let ctx = ctx_with(&[("checkin_streak", Value::Int(10))]);
        assert!(evaluate("checkin_streak >= 7", &ctx).unwrap());
    }

    #[test]
    fn eval_simple_false() {
        let ctx = ctx_with(&[
            ("checkin_streak", Value::Int(10)),
            ("submission_count", Value::Int(1)),
        ]);
        assert!(!evaluate("checkin_streak >= 7 AND submission_count >= 3", &ctx).unwrap());
    }

    #[test]
    fn eval_and_true() {
        let ctx = ctx_with(&[
            ("checkin_streak", Value::Int(10)),
            ("submission_count", Value::Int(5)),
        ]);
        assert!(evaluate("checkin_streak >= 7 AND submission_count >= 3", &ctx).unwrap());
    }

    #[test]
    fn eval_or() {
        let ctx = ctx_with(&[
            ("checkin_streak", Value::Int(3)),
            ("badge_count", Value::Int(5)),
        ]);
        assert!(evaluate("checkin_streak >= 7 OR badge_count >= 5", &ctx).unwrap());
    }

    #[test]
    fn eval_not() {
        let ctx = ctx_with(&[("badge_count", Value::Int(2))]);
        assert!(evaluate("NOT badge_count >= 5", &ctx).unwrap());
    }

    #[test]
    fn eval_missing_variable() {
        let ctx = EvalContext::new();
        let result = evaluate("checkin_streak >= 7", &ctx);
        assert!(matches!(result, Err(EvalError::MissingVariable(_))));
    }

    #[test]
    fn eval_string_comparison() {
        let ctx = ctx_with(&[("event.type", Value::String("checkin".into()))]);
        assert!(evaluate("event.type == \"checkin\"", &ctx).unwrap());
    }

    #[test]
    fn eval_count_function() {
        let ctx = ctx_with(&[("submissions_last_7_days", Value::Int(6))]);
        assert!(evaluate("count(submissions, last_7_days) >= 5", &ctx).unwrap());
    }

    #[test]
    fn eval_day_of_week() {
        let ctx = ctx_with(&[("event.occurred_at.day_of_week", Value::Int(5))]);
        assert!(evaluate("day_of_week(event.occurred_at) == 5", &ctx).unwrap());
    }

    #[test]
    fn eval_nested_parens() {
        let ctx = ctx_with(&[
            ("checkin_streak", Value::Int(3)),
            ("badge_count", Value::Int(6)),
            ("submission_count", Value::Int(5)),
        ]);
        assert!(
            evaluate(
                "(checkin_streak >= 7 OR badge_count >= 5) AND submission_count >= 3",
                &ctx
            )
            .unwrap()
        );
    }
}
