use serde::{Deserialize, Serialize};

use crate::types::{BUILTIN_FUNCS, BUILTIN_VARS};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    pub label: String,
    pub kind: SuggestionKind,
    pub detail: Option<String>,
    pub insert_text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SuggestionKind {
    Variable,
    Operator,
    Function,
    Keyword,
}

/// Return autocomplete suggestions for the given source and cursor position.
pub fn complete(source: &str, cursor_pos: usize) -> Vec<Suggestion> {
    let prefix = &source[..cursor_pos.min(source.len())];
    let token_start = prefix
        .rfind(|c: char| c.is_whitespace() || c == '(' || c == ',')
        .map(|i| i + 1)
        .unwrap_or(0);
    let current_token = &prefix[token_start..];

    // Determine context: are we after a comparison (expect operator)?
    let trimmed = prefix.trim_end();
    let after_value = trimmed
        .chars()
        .last()
        .map(|c| c.is_alphanumeric() || c == '_' || c == '"' || c.is_ascii_digit())
        .unwrap_or(false);

    // Check if we're right after a comparison operator (expect value/variable)
    let after_operator = trimmed.ends_with(">=")
        || trimmed.ends_with("<=")
        || trimmed.ends_with("==")
        || trimmed.ends_with("!=")
        || (trimmed.ends_with('>') && !trimmed.ends_with(">="))
        || (trimmed.ends_with('<') && !trimmed.ends_with("<="));

    let mut suggestions = Vec::new();

    if after_operator || current_token.is_empty() && !after_value {
        // Suggest variables and functions
        add_variable_suggestions(current_token, &mut suggestions);
        add_function_suggestions(current_token, &mut suggestions);
    } else if after_value && current_token.is_empty() {
        // After a complete value, suggest operators
        add_operator_suggestions(&mut suggestions);
        add_logical_suggestions(&mut suggestions);
    } else {
        // Partial token — filter variables, functions, and keywords
        add_variable_suggestions(current_token, &mut suggestions);
        add_function_suggestions(current_token, &mut suggestions);
        add_logical_suggestions_filtered(current_token, &mut suggestions);
    }

    suggestions
}

fn add_variable_suggestions(prefix: &str, suggestions: &mut Vec<Suggestion>) {
    let lower = prefix.to_lowercase();
    for var in BUILTIN_VARS {
        if var.name.to_lowercase().starts_with(&lower) {
            suggestions.push(Suggestion {
                label: var.name.to_string(),
                kind: SuggestionKind::Variable,
                detail: Some(var.var_type.to_string()),
                insert_text: var.name.to_string(),
            });
        }
    }
}

fn add_function_suggestions(prefix: &str, suggestions: &mut Vec<Suggestion>) {
    let lower = prefix.to_lowercase();
    for func in BUILTIN_FUNCS {
        if func.name.to_lowercase().starts_with(&lower) {
            suggestions.push(Suggestion {
                label: func.name.to_string(),
                kind: SuggestionKind::Function,
                detail: Some(func.signature.to_string()),
                insert_text: format!("{}(", func.name),
            });
        }
    }
}

fn add_operator_suggestions(suggestions: &mut Vec<Suggestion>) {
    for (symbol, detail) in [
        ("==", "equals"),
        ("!=", "not equals"),
        (">", "greater than"),
        (">=", "greater than or equal"),
        ("<", "less than"),
        ("<=", "less than or equal"),
    ] {
        suggestions.push(Suggestion {
            label: symbol.to_string(),
            kind: SuggestionKind::Operator,
            detail: Some(detail.to_string()),
            insert_text: symbol.to_string(),
        });
    }
}

fn add_logical_suggestions(suggestions: &mut Vec<Suggestion>) {
    for kw in ["AND", "OR"] {
        suggestions.push(Suggestion {
            label: kw.to_string(),
            kind: SuggestionKind::Keyword,
            detail: Some("logical operator".to_string()),
            insert_text: kw.to_string(),
        });
    }
}

fn add_logical_suggestions_filtered(prefix: &str, suggestions: &mut Vec<Suggestion>) {
    let upper = prefix.to_uppercase();
    for kw in ["AND", "OR", "NOT"] {
        if kw.starts_with(&upper) {
            suggestions.push(Suggestion {
                label: kw.to_string(),
                kind: SuggestionKind::Keyword,
                detail: Some("logical operator".to_string()),
                insert_text: kw.to_string(),
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn complete_variable_prefix() {
        let results = complete("check", 5);
        let labels: Vec<_> = results.iter().map(|s| s.label.as_str()).collect();
        assert!(labels.contains(&"checkin_count"));
        assert!(labels.contains(&"checkin_streak"));
    }

    #[test]
    fn complete_after_comparison() {
        let results = complete("checkin_streak >= 7 ", 20);
        let labels: Vec<_> = results.iter().map(|s| s.label.as_str()).collect();
        assert!(labels.contains(&"AND"));
        assert!(labels.contains(&"OR"));
    }

    #[test]
    fn complete_function_prefix() {
        let results = complete("cou", 3);
        let labels: Vec<_> = results.iter().map(|s| s.label.as_str()).collect();
        assert!(labels.contains(&"count"));
    }
}
