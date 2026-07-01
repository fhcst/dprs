#![cfg(feature = "python")]
use pyo3::prelude::*;

use crate::types::EvalContext;

/// Parse a DSL expression. Returns JSON string with AST or errors.
#[pyfunction]
fn parse(source: &str) -> String {
    match crate::parse(source) {
        Ok(ast) => serde_json::to_string(&serde_json::json!({"ok": true, "ast": ast}))
            .unwrap_or_default(),
        Err(errors) => {
            serde_json::to_string(&serde_json::json!({"ok": false, "errors": errors}))
                .unwrap_or_default()
        }
    }
}

/// Validate a DSL expression. Returns JSON string with diagnostics.
#[pyfunction]
fn validate(source: &str) -> String {
    let diagnostics = crate::validate(source);
    serde_json::to_string(&diagnostics).unwrap_or_default()
}

/// Evaluate a DSL expression against a JSON context string. Returns JSON result.
#[pyfunction]
fn evaluate(source: &str, context_json: &str) -> String {
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
#[pyfunction]
fn complete(source: &str, cursor_pos: usize) -> String {
    let suggestions = crate::complete(source, cursor_pos);
    serde_json::to_string(&suggestions).unwrap_or_default()
}

/// Return hover information as JSON.
#[pyfunction]
fn hover_info(source: &str, cursor_pos: usize) -> String {
    let info = crate::hover_info(source, cursor_pos);
    serde_json::to_string(&info).unwrap_or_default()
}

/// Describe a DSL expression as locale-specific Markdown.
#[pyfunction]
fn describe(source: &str, locale: &str) -> String {
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
#[pyfunction]
fn get_help_content(locale: &str) -> String {
    let content = crate::get_help_content(locale);
    serde_json::to_string(&content).unwrap_or_default()
}

/// Python module definition.
#[pymodule]
fn dsl_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    m.add_function(wrap_pyfunction!(complete, m)?)?;
    m.add_function(wrap_pyfunction!(hover_info, m)?)?;
    m.add_function(wrap_pyfunction!(describe, m)?)?;
    m.add_function(wrap_pyfunction!(get_help_content, m)?)?;
    Ok(())
}
