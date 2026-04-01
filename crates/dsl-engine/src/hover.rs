use serde::{Deserialize, Serialize};

use crate::types::{BUILTIN_FUNCS, BUILTIN_VARS};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeInfo {
    pub name: String,
    #[serde(rename = "type")]
    pub var_type: String,
    pub description: String,
}

/// Return hover information for the token at the given position.
pub fn hover_info(source: &str, cursor_pos: usize) -> Option<TypeInfo> {
    let token = extract_token_at(source, cursor_pos)?;
    lookup_token(&token)
}

/// Extract the identifier token at or around the cursor position.
fn extract_token_at(source: &str, pos: usize) -> Option<String> {
    if pos > source.len() {
        return None;
    }

    let bytes = source.as_bytes();

    // Find token start: scan backwards from cursor
    let mut start = pos;
    while start > 0
        && (bytes[start - 1].is_ascii_alphanumeric()
            || bytes[start - 1] == b'_'
            || bytes[start - 1] == b'.')
    {
        start -= 1;
    }

    // Find token end: scan forwards from cursor
    let mut end = pos;
    while end < source.len()
        && (bytes[end].is_ascii_alphanumeric() || bytes[end] == b'_' || bytes[end] == b'.')
    {
        end += 1;
    }

    if start == end {
        return None;
    }

    Some(source[start..end].to_string())
}

fn lookup_token(token: &str) -> Option<TypeInfo> {
    // Check built-in variables
    for var in BUILTIN_VARS {
        if var.name == token {
            return Some(TypeInfo {
                name: var.name.to_string(),
                var_type: var.var_type.to_string(),
                description: get_locale_description(var.description_key, "tw"),
            });
        }
    }

    // Check built-in functions
    for func in BUILTIN_FUNCS {
        if func.name == token {
            return Some(TypeInfo {
                name: func.name.to_string(),
                var_type: format!("fn → {}", func.return_type),
                description: get_locale_description(func.description_key, "tw"),
            });
        }
    }

    None
}

fn get_locale_description(key: &str, _locale: &str) -> String {
    // Default to Traditional Chinese descriptions
    match key {
        "var.checkin_count" => "總打卡次數".to_string(),
        "var.checkin_streak" => "連續打卡天數".to_string(),
        "var.submission_count" => "總繳交次數".to_string(),
        "var.points" => "目前點數".to_string(),
        "var.badge_count" => "已獲得徽章數".to_string(),
        "var.event_type" => "事件類型（\"checkin\" | \"submission\" | \"manual\"）".to_string(),
        "var.event_occurred_at" => "事件發生時間".to_string(),
        "func.count" => "計算指定時間窗口內的次數".to_string(),
        "func.day_of_week" => "取得星期幾（0=一 ~ 6=日）".to_string(),
        _ => key.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hover_on_variable() {
        let info = hover_info("checkin_streak >= 7", 5).unwrap();
        assert_eq!(info.name, "checkin_streak");
        assert_eq!(info.var_type, "int");
        assert!(info.description.contains("連續打卡"));
    }

    #[test]
    fn hover_on_function() {
        let info = hover_info("count(submissions, last_7_days) >= 5", 2).unwrap();
        assert_eq!(info.name, "count");
        assert!(info.var_type.contains("fn"));
    }

    #[test]
    fn hover_on_number_returns_none() {
        let info = hover_info("checkin_streak >= 7", 19);
        assert!(info.is_none());
    }

    #[test]
    fn hover_on_dot_notation() {
        let info = hover_info("event.type == \"checkin\"", 5).unwrap();
        assert_eq!(info.name, "event.type");
        assert_eq!(info.var_type, "string");
    }
}
