use wasm_bindgen::prelude::*;

use crate::types::EvalContext;

/// Parse a DSL expression and return the AST or errors as JSON.
#[wasm_bindgen]
pub fn parse(source: &str) -> String {
    match crate::parse(source) {
        Ok(ast) => serde_json::to_string(&serde_json::json!({"ok": true, "ast": ast}))
            .unwrap_or_default(),
        Err(errors) => {
            serde_json::to_string(&serde_json::json!({"ok": false, "errors": errors}))
                .unwrap_or_default()
        }
    }
}

/// Validate a DSL expression and return diagnostics as JSON.
#[wasm_bindgen]
pub fn validate(source: &str) -> String {
    let diagnostics = crate::validate(source);
    serde_json::to_string(&diagnostics).unwrap_or_default()
}

/// Evaluate a DSL expression against a JSON context. Returns JSON result.
#[wasm_bindgen]
pub fn evaluate(source: &str, context_json: &str) -> String {
    let context: EvalContext = match serde_json::from_str(context_json) {
        Ok(ctx) => ctx,
        Err(e) => {
            return serde_json::to_string(&serde_json::json!({
                "ok": false, "error": format!("Invalid context JSON: {}", e)
            }))
            .unwrap_or_default();
        }
    };
    match crate::evaluate(source, &context) {
        Ok(result) => {
            serde_json::to_string(&serde_json::json!({"ok": true, "result": result}))
                .unwrap_or_default()
        }
        Err(e) => serde_json::to_string(
            &serde_json::json!({"ok": false, "error": e.to_string()}),
        )
        .unwrap_or_default(),
    }
}

/// Return autocomplete suggestions as JSON.
#[wasm_bindgen]
pub fn complete(source: &str, cursor_pos: usize) -> String {
    let suggestions = crate::complete(source, cursor_pos);
    serde_json::to_string(&suggestions).unwrap_or_default()
}

/// Return hover information as JSON, or null if no info available.
#[wasm_bindgen]
pub fn hover_info(source: &str, cursor_pos: usize) -> String {
    let info = crate::hover_info(source, cursor_pos);
    serde_json::to_string(&info).unwrap_or_default()
}

/// Describe a DSL expression as locale-specific Markdown.
#[wasm_bindgen]
pub fn describe(source: &str, locale: &str) -> String {
    match crate::describe(source, locale) {
        Ok(md) => {
            serde_json::to_string(&serde_json::json!({"ok": true, "markdown": md}))
                .unwrap_or_default()
        }
        Err(errors) => {
            serde_json::to_string(&serde_json::json!({"ok": false, "errors": errors}))
                .unwrap_or_default()
        }
    }
}

/// Return structured help content as JSON.
#[wasm_bindgen]
pub fn get_help_content(locale: &str) -> String {
    let content = crate::get_help_content(locale);
    serde_json::to_string(&content).unwrap_or_default()
}
