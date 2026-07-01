use pest::Parser;

use crate::ast::{CompareOp, Expr, FuncArg};
use crate::error::{ParseError, Span};
use crate::grammar::{DslParser, Rule};

/// Parse a DSL expression string into an AST.
pub fn parse(source: &str) -> Result<Expr, Vec<ParseError>> {
    let pairs = DslParser::parse(Rule::program, source).map_err(|e| {
        let (line, col) = match e.line_col {
            pest::error::LineColLocation::Pos((l, c)) => (l, c),
            pest::error::LineColLocation::Span((l, c), _) => (l, c),
        };
        let location = match &e.location {
            pest::error::InputLocation::Pos(p) => *p,
            pest::error::InputLocation::Span((s, _)) => *s,
        };
        vec![ParseError {
            message: format!("{}", e),
            span: Span {
                start: location,
                end: location + 1,
                line,
                col,
            },
        }]
    })?;

    let program = pairs.into_iter().next().unwrap();
    let expr_pair = program
        .into_inner()
        .find(|p| p.as_rule() == Rule::expression)
        .unwrap();

    parse_expression(expr_pair).map_err(|e| vec![e])
}

fn parse_expression(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let inner = pair.into_inner().next().unwrap();
    parse_or_expr(inner)
}

fn parse_or_expr(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let mut inner = pair.into_inner();
    let mut left = parse_and_expr(inner.next().unwrap())?;

    while inner.peek().is_some() {
        let _op = inner.next().unwrap(); // or_op
        let right = parse_and_expr(inner.next().unwrap())?;
        left = Expr::Or(Box::new(left), Box::new(right));
    }

    Ok(left)
}

fn parse_and_expr(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let mut inner = pair.into_inner();
    let mut left = parse_not_expr(inner.next().unwrap())?;

    while inner.peek().is_some() {
        let _op = inner.next().unwrap(); // and_op
        let right = parse_not_expr(inner.next().unwrap())?;
        left = Expr::And(Box::new(left), Box::new(right));
    }

    Ok(left)
}

fn parse_not_expr(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let mut inner = pair.into_inner();
    let first = inner.next().unwrap();

    match first.as_rule() {
        Rule::not_op => {
            let operand = parse_not_expr(inner.next().unwrap())?;
            Ok(Expr::Not(Box::new(operand)))
        }
        Rule::comparison => parse_comparison(first),
        _ => unreachable!("Unexpected rule in not_expr: {:?}", first.as_rule()),
    }
}

fn parse_comparison(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let mut inner = pair.into_inner();
    let left = parse_value(inner.next().unwrap())?;

    if let Some(op_pair) = inner.next() {
        let op = parse_compare_op(op_pair)?;
        let right = parse_value(inner.next().unwrap())?;
        Ok(Expr::Compare {
            left: Box::new(left),
            op,
            right: Box::new(right),
        })
    } else {
        Ok(left)
    }
}

fn parse_compare_op(pair: pest::iterators::Pair<Rule>) -> Result<CompareOp, ParseError> {
    match pair.as_str() {
        "==" => Ok(CompareOp::Eq),
        "!=" => Ok(CompareOp::Ne),
        ">" => Ok(CompareOp::Gt),
        ">=" => Ok(CompareOp::Ge),
        "<" => Ok(CompareOp::Lt),
        "<=" => Ok(CompareOp::Le),
        other => Err(make_error(&pair, format!("Unknown operator: {}", other))),
    }
}

fn parse_value(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let inner = pair.into_inner().next().unwrap();
    match inner.as_rule() {
        Rule::func_call => parse_func_call(inner),
        Rule::literal => parse_literal(inner),
        Rule::variable => Ok(Expr::Var(inner.as_str().to_string())),
        Rule::expression => {
            let expr = parse_expression(inner)?;
            Ok(Expr::Group(Box::new(expr)))
        }
        _ => unreachable!("Unexpected rule in value: {:?}", inner.as_rule()),
    }
}

fn parse_literal(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let inner = pair.into_inner().next().unwrap();
    match inner.as_rule() {
        Rule::int_lit => {
            let val: i64 = inner
                .as_str()
                .parse()
                .map_err(|_| make_error(&inner, "Invalid integer".into()))?;
            Ok(Expr::IntLit(val))
        }
        Rule::float_lit => {
            let val: f64 = inner
                .as_str()
                .parse()
                .map_err(|_| make_error(&inner, "Invalid float".into()))?;
            Ok(Expr::FloatLit(val))
        }
        Rule::string_lit => {
            let raw = inner.as_str();
            // Strip surrounding quotes
            let content = &raw[1..raw.len() - 1];
            Ok(Expr::StringLit(content.to_string()))
        }
        Rule::bool_lit => {
            let val = inner.as_str().eq_ignore_ascii_case("true");
            Ok(Expr::BoolLit(val))
        }
        _ => unreachable!("Unexpected rule in literal: {:?}", inner.as_rule()),
    }
}

fn parse_func_call(pair: pest::iterators::Pair<Rule>) -> Result<Expr, ParseError> {
    let mut inner = pair.into_inner();
    let name = inner.next().unwrap().as_str().to_string();
    let args_pair = inner.next().unwrap();

    let mut args = Vec::new();
    for arg_pair in args_pair.into_inner() {
        let arg_inner = arg_pair.into_inner().next().unwrap();
        let arg = match arg_inner.as_rule() {
            Rule::time_window => {
                let s = arg_inner.as_str();
                // Extract N from "last_N_days"
                let n: u32 = s
                    .strip_prefix("last_")
                    .and_then(|s| s.strip_suffix("_days"))
                    .and_then(|s| s.parse().ok())
                    .ok_or_else(|| make_error(&arg_inner, "Invalid time window".into()))?;
                FuncArg::TimeWindow(n)
            }
            Rule::variable => FuncArg::Ident(arg_inner.as_str().to_string()),
            Rule::literal => {
                let expr = parse_literal(arg_inner)?;
                FuncArg::Expr(Box::new(expr))
            }
            _ => unreachable!("Unexpected rule in func_arg: {:?}", arg_inner.as_rule()),
        };
        args.push(arg);
    }

    Ok(Expr::FuncCall { name, args })
}

fn make_error(pair: &pest::iterators::Pair<Rule>, message: String) -> ParseError {
    let span = pair.as_span();
    let (line, col) = span.start_pos().line_col();
    ParseError {
        message,
        span: Span {
            start: span.start(),
            end: span.end(),
            line,
            col,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_simple_comparison() {
        let result = parse("checkin_streak >= 7").unwrap();
        assert!(matches!(result, Expr::Compare { .. }));
    }

    #[test]
    fn parse_and_expression() {
        let result = parse("checkin_streak >= 7 AND submission_count >= 3").unwrap();
        assert!(matches!(result, Expr::And(_, _)));
    }

    #[test]
    fn parse_or_expression() {
        let result = parse("checkin_streak >= 7 OR badge_count >= 5").unwrap();
        assert!(matches!(result, Expr::Or(_, _)));
    }

    #[test]
    fn parse_not_expression() {
        let result = parse("NOT badge_count >= 5").unwrap();
        assert!(matches!(result, Expr::Not(_)));
    }

    #[test]
    fn parse_nested_parens() {
        let result =
            parse("(checkin_streak >= 7 OR badge_count >= 5) AND submission_count >= 3").unwrap();
        assert!(matches!(result, Expr::And(_, _)));
    }

    #[test]
    fn parse_func_call() {
        let result = parse("count(submissions, last_7_days) >= 5").unwrap();
        assert!(matches!(result, Expr::Compare { .. }));
    }

    #[test]
    fn parse_string_comparison() {
        let result = parse("event.type == \"checkin\"").unwrap();
        assert!(matches!(result, Expr::Compare { .. }));
    }

    #[test]
    fn parse_bool_literal() {
        let result = parse("true").unwrap();
        assert!(matches!(result, Expr::BoolLit(true)));
    }

    #[test]
    fn parse_invalid_syntax() {
        let result = parse("checkin_streak >= AND 7");
        assert!(result.is_err());
    }

    #[test]
    fn parse_complex_expression() {
        let result = parse(
            "checkin_streak >= 7 AND submission_count >= 3 OR count(submissions, last_7_days) >= 5",
        )
        .unwrap();
        // OR has lower precedence, so this is (streak >= 7 AND count >= 3) OR (func >= 5)
        assert!(matches!(result, Expr::Or(_, _)));
    }

    #[test]
    fn parse_day_of_week_func() {
        let result = parse("day_of_week(event.occurred_at) == 5").unwrap();
        assert!(matches!(result, Expr::Compare { .. }));
    }
}
