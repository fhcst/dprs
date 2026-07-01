use serde::{Deserialize, Serialize};

use crate::types::{BUILTIN_FUNCS, BUILTIN_VARS};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpContent {
    pub variables: Vec<HelpVariable>,
    pub operators: Vec<HelpOperator>,
    pub functions: Vec<HelpFunction>,
    pub examples: Vec<HelpExample>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpVariable {
    pub name: String,
    #[serde(rename = "type")]
    pub var_type: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpOperator {
    pub symbol: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpFunction {
    pub signature: String,
    pub description: String,
    pub example: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpExample {
    pub expression: String,
    pub description: String,
}

/// Return structured help content for the DSL, localized.
pub fn get_help_content(locale: &str) -> HelpContent {
    HelpContent {
        variables: build_variables(locale),
        operators: build_operators(locale),
        functions: build_functions(locale),
        examples: build_examples(locale),
    }
}

fn build_variables(locale: &str) -> Vec<HelpVariable> {
    BUILTIN_VARS
        .iter()
        .map(|v| HelpVariable {
            name: v.name.to_string(),
            var_type: localize_type(v.var_type, locale),
            description: localize_var_desc(v.description_key, locale),
        })
        .collect()
}

fn build_operators(locale: &str) -> Vec<HelpOperator> {
    let ops = match locale {
        "tw" => vec![
            ("==", "等於"),
            ("!=", "不等於"),
            (">", "大於"),
            (">=", "大於等於"),
            ("<", "小於"),
            ("<=", "小於等於"),
            ("AND", "且（兩個條件都要成立）"),
            ("OR", "或（任一條件成立即可）"),
            ("NOT", "非（反轉條件）"),
        ],
        _ => vec![
            ("==", "equals"),
            ("!=", "not equals"),
            (">", "greater than"),
            (">=", "greater than or equal"),
            ("<", "less than"),
            ("<=", "less than or equal"),
            ("AND", "both conditions must be true"),
            ("OR", "either condition can be true"),
            ("NOT", "negates a condition"),
        ],
    };
    ops.into_iter()
        .map(|(s, d)| HelpOperator {
            symbol: s.to_string(),
            description: d.to_string(),
        })
        .collect()
}

fn build_functions(locale: &str) -> Vec<HelpFunction> {
    BUILTIN_FUNCS
        .iter()
        .map(|f| HelpFunction {
            signature: f.signature.to_string(),
            description: localize_func_desc(f.description_key, locale),
            example: f.example.to_string(),
        })
        .collect()
}

fn build_examples(locale: &str) -> Vec<HelpExample> {
    match locale {
        "tw" => vec![
            HelpExample {
                expression: "checkin_streak >= 7".to_string(),
                description: "連續打卡 7 天".to_string(),
            },
            HelpExample {
                expression: "checkin_streak >= 7 AND submission_count >= 3".to_string(),
                description: "打卡＋繳交都達標".to_string(),
            },
            HelpExample {
                expression: "count(submissions, last_7_days) >= 5".to_string(),
                description: "近 7 天內繳交 5 次以上".to_string(),
            },
            HelpExample {
                expression: "day_of_week(event.occurred_at) >= 5 AND checkin_streak >= 3"
                    .to_string(),
                description: "週末打卡且連續 3 天".to_string(),
            },
            HelpExample {
                expression: "badge_count >= 5".to_string(),
                description: "集滿 5 個徽章的「收藏家」成就".to_string(),
            },
        ],
        _ => vec![
            HelpExample {
                expression: "checkin_streak >= 7".to_string(),
                description: "7-day consecutive check-in".to_string(),
            },
            HelpExample {
                expression: "checkin_streak >= 7 AND submission_count >= 3".to_string(),
                description: "Check-in and submission targets met".to_string(),
            },
            HelpExample {
                expression: "count(submissions, last_7_days) >= 5".to_string(),
                description: "5+ submissions in the last 7 days".to_string(),
            },
        ],
    }
}

fn localize_type(type_name: &str, locale: &str) -> String {
    if locale != "tw" {
        return type_name.to_string();
    }
    match type_name {
        "int" => "整數".to_string(),
        "float" => "小數".to_string(),
        "string" => "字串".to_string(),
        "bool" => "布林".to_string(),
        "datetime" => "日期時間".to_string(),
        other => other.to_string(),
    }
}

fn localize_var_desc(key: &str, locale: &str) -> String {
    if locale != "tw" {
        return match key {
            "var.checkin_count" => "Total check-in count",
            "var.checkin_streak" => "Consecutive check-in days",
            "var.submission_count" => "Total submission count",
            "var.points" => "Current points",
            "var.badge_count" => "Number of earned badges",
            "var.event_type" => "Event type (\"checkin\" | \"submission\" | \"manual\")",
            "var.event_occurred_at" => "Event occurrence time",
            _ => key,
        }
        .to_string();
    }
    match key {
        "var.checkin_count" => "總打卡次數".to_string(),
        "var.checkin_streak" => "連續打卡天數".to_string(),
        "var.submission_count" => "總繳交次數".to_string(),
        "var.points" => "目前點數".to_string(),
        "var.badge_count" => "已獲得徽章數".to_string(),
        "var.event_type" => "事件類型（\"checkin\" | \"submission\" | \"manual\"）".to_string(),
        "var.event_occurred_at" => "事件發生時間".to_string(),
        _ => key.to_string(),
    }
}

fn localize_func_desc(key: &str, locale: &str) -> String {
    if locale != "tw" {
        return match key {
            "func.count" => "Count occurrences within a time window",
            "func.day_of_week" => "Get day of week (0=Mon ~ 6=Sun)",
            _ => key,
        }
        .to_string();
    }
    match key {
        "func.count" => "計算指定時間窗口內的次數".to_string(),
        "func.day_of_week" => "取得星期幾（0=一 ~ 6=日）".to_string(),
        _ => key.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn help_tw_has_all_sections() {
        let content = get_help_content("tw");
        assert_eq!(content.variables.len(), 7);
        assert_eq!(content.operators.len(), 9);
        assert_eq!(content.functions.len(), 2);
        assert!(content.examples.len() >= 3);
    }

    #[test]
    fn help_tw_types_localized() {
        let content = get_help_content("tw");
        let checkin = content.variables.iter().find(|v| v.name == "checkin_count").unwrap();
        assert_eq!(checkin.var_type, "整數");
    }

    #[test]
    fn help_en_fallback() {
        let content = get_help_content("en");
        let checkin = content.variables.iter().find(|v| v.name == "checkin_count").unwrap();
        assert_eq!(checkin.var_type, "int");
    }

    #[test]
    fn help_examples_have_expressions() {
        let content = get_help_content("tw");
        for example in &content.examples {
            assert!(!example.expression.is_empty());
            assert!(!example.description.is_empty());
        }
    }
}
