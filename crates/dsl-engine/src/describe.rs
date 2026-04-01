use crate::ast::{CompareOp, Expr, FuncArg};
use crate::error::ParseError;

/// Convert a valid DSL expression into a locale-specific Markdown summary.
pub fn describe(source: &str, locale: &str) -> Result<String, Vec<ParseError>> {
    let ast = crate::parse(source)?;
    Ok(describe_expr(&ast, locale))
}

fn describe_expr(expr: &Expr, locale: &str) -> String {
    match expr {
        Expr::And(_left, _right) => {
            let items = collect_and_items(expr);
            let bullets: Vec<String> = items.iter().map(|e| describe_condition(e, locale)).collect();
            let header = match locale {
                "tw" => "**獲得條件：**",
                _ => "**Conditions:**",
            };
            format!(
                "{}\n{}",
                header,
                bullets
                    .iter()
                    .map(|b| format!("- {}", b))
                    .collect::<Vec<_>>()
                    .join("\n")
            )
        }
        Expr::Or(left, right) => {
            let left_desc = describe_expr(left, locale);
            let right_desc = describe_expr(right, locale);
            let separator = match locale {
                "tw" => "或",
                _ => "or",
            };
            format!("{}\n\n{} {}", left_desc, separator, right_desc)
        }
        _ => {
            let header = match locale {
                "tw" => "**獲得條件：**",
                _ => "**Conditions:**",
            };
            format!("{}\n- {}", header, describe_condition(expr, locale))
        }
    }
}

/// Collect all items connected by AND into a flat list.
fn collect_and_items(expr: &Expr) -> Vec<&Expr> {
    let mut items = Vec::new();
    match expr {
        Expr::And(left, right) => {
            items.extend(collect_and_items(left));
            items.extend(collect_and_items(right));
        }
        other => items.push(other),
    }
    items
}

fn describe_condition(expr: &Expr, locale: &str) -> String {
    match expr {
        Expr::Compare { left, op, right } => describe_comparison(left, *op, right, locale),
        Expr::Not(inner) => {
            let desc = describe_condition(inner, locale);
            match locale {
                "tw" => format!("非{}", desc),
                _ => format!("NOT {}", desc),
            }
        }
        Expr::Group(inner) => describe_condition(inner, locale),
        Expr::BoolLit(true) => match locale {
            "tw" => "永遠成立".to_string(),
            _ => "always true".to_string(),
        },
        Expr::BoolLit(false) => match locale {
            "tw" => "永遠不成立".to_string(),
            _ => "always false".to_string(),
        },
        Expr::FuncCall { name, args } => describe_func(name, args, locale),
        _ => format!("{:?}", expr),
    }
}

fn describe_comparison(left: &Expr, op: CompareOp, right: &Expr, locale: &str) -> String {
    let var_desc = describe_var_or_func(left, locale);
    let op_desc = describe_op(op, locale);
    let val = describe_value(right);

    match locale {
        "tw" => format!("{}{}**{}**", var_desc, op_desc, val),
        _ => format!("{} {} **{}**", var_desc, op.as_str(), val),
    }
}

fn describe_var_or_func(expr: &Expr, locale: &str) -> String {
    match expr {
        Expr::Var(name) => describe_var_name(name, locale),
        Expr::FuncCall { name, args } => describe_func(name, args, locale),
        _ => format!("{:?}", expr),
    }
}

fn describe_var_name(name: &str, locale: &str) -> String {
    if locale != "tw" {
        return name.to_string();
    }
    match name {
        "checkin_count" => "總打卡次數".to_string(),
        "checkin_streak" => "連續打卡達 ".to_string(),
        "submission_count" => "繳交次數".to_string(),
        "points" => "點數".to_string(),
        "badge_count" => "已獲得徽章數".to_string(),
        "event.type" => "事件類型".to_string(),
        _ => name.to_string(),
    }
}

fn describe_func(name: &str, args: &[FuncArg], locale: &str) -> String {
    match (name, locale) {
        ("count", "tw") => {
            let source = match args.first() {
                Some(FuncArg::Ident(id)) if id == "submissions" => "繳交",
                Some(FuncArg::Ident(id)) if id == "checkins" => "打卡",
                _ => "項目",
            };
            let days = match args.get(1) {
                Some(FuncArg::TimeWindow(n)) => *n,
                _ => 0,
            };
            format!("近 {} 天{}次數", days, source)
        }
        ("day_of_week", "tw") => "星期".to_string(),
        _ => format!("{}(…)", name),
    }
}

fn describe_op(op: CompareOp, locale: &str) -> String {
    if locale != "tw" {
        return format!(" {} ", op.as_str());
    }
    match op {
        CompareOp::Ge => "達 ".to_string(),
        CompareOp::Gt => "超過 ".to_string(),
        CompareOp::Le => "不超過 ".to_string(),
        CompareOp::Lt => "低於 ".to_string(),
        CompareOp::Eq => "為 ".to_string(),
        CompareOp::Ne => "不為 ".to_string(),
    }
}

fn describe_value(expr: &Expr) -> String {
    match expr {
        Expr::IntLit(v) => v.to_string(),
        Expr::FloatLit(v) => v.to_string(),
        Expr::StringLit(v) => v.clone(),
        Expr::BoolLit(v) => v.to_string(),
        _ => format!("{:?}", expr),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn describe_simple_condition() {
        let result = describe("checkin_streak >= 7", "tw").unwrap();
        assert!(result.contains("連續打卡"));
        assert!(result.contains("**7**"));
    }

    #[test]
    fn describe_and_as_bullet_list() {
        let result =
            describe("checkin_streak >= 7 AND submission_count >= 3", "tw").unwrap();
        assert!(result.contains("- "));
        // Should have two bullet points
        let bullet_count = result.matches("- ").count();
        assert_eq!(bullet_count, 2);
    }

    #[test]
    fn describe_count_function() {
        let result =
            describe("count(submissions, last_7_days) >= 5", "tw").unwrap();
        assert!(result.contains("近 7 天"));
        assert!(result.contains("繳交"));
    }

    #[test]
    fn describe_english_locale() {
        let result = describe("checkin_streak >= 7", "en").unwrap();
        assert!(result.contains("Conditions"));
    }
}
