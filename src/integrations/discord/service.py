"""Discord Webhook integration service."""
import logging

import httpx

logger = logging.getLogger(__name__)

_EMBED_COLOR = 0x7C3AED  # brand purple
_MAX_DESC = 200

# Discord embed field limits
_TITLE_MAX = 256
_DESC_MAX = 4096
_FOOTER_MAX = 2048

# System default templates
_DEFAULT_TITLE = "{task_name} — {date}"
_DEFAULT_FOOTER = "每日訓練提交系統"


class SafeDict(dict):
    """Dict subclass that returns the placeholder for missing keys.

    Used with str.format_map() to leave unknown variables as-is
    (e.g. ``{unknown}`` stays ``{unknown}``).
    """

    def __missing__(self, key: str) -> str:
        logger.warning("Template variable not found: {%s}", key)
        return "{" + key + "}"


def render_template(template: str, variables: dict[str, str]) -> str:
    """Render a template string with variable substitution.

    Uses SafeDict so undefined variables are preserved as-is.
    Malformed braces (single ``{``) fall back to the original template.
    """
    try:
        return template.format_map(SafeDict(variables))
    except (ValueError, KeyError):
        logger.warning("Template rendering failed, returning original: %s", template)
        return template


def resolve_template_field(
    override: str | None,
    class_default: str | None,
    system_default: str,
) -> str:
    """Three-layer fallback: task override > class default > system default.

    Empty strings are treated as "not set" and trigger fallback.
    """
    if override:
        return override
    if class_default:
        return class_default
    return system_default


def truncate_field(text: str, max_length: int) -> str:
    """Truncate text to max_length, appending '...' if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


async def send_task_embed(
    webhook_url: str,
    task_name: str,
    description: str,
    date: str | None,
    *,
    class_template: dict | None = None,
    title_override: str | None = None,
    description_override: str | None = None,
    footer_override: str | None = None,
    class_name: str | None = None,
    site_name: str | None = None,
) -> None:
    """Send a task assignment embed to a Discord Webhook URL.

    Supports template-driven rendering with three-layer fallback:
    task override > class default > system default.

    Errors are logged and swallowed — callers must not depend on this succeeding.
    """
    ct = class_template or {}

    # Resolve each field via three-layer fallback
    title_tmpl = resolve_template_field(
        title_override,
        ct.get("title_format"),
        _DEFAULT_TITLE,
    )
    desc_tmpl = resolve_template_field(
        description_override,
        ct.get("description_template"),
        description[:_MAX_DESC] + "..." if len(description) > _MAX_DESC else description,
    )
    footer_tmpl = resolve_template_field(
        footer_override,
        ct.get("footer_text"),
        site_name or _DEFAULT_FOOTER,
    )

    # Build variable context
    variables = {
        "task_name": task_name,
        "date": date or "",
        "class_name": class_name or "",
        "description": description,
    }

    # Render templates with variable interpolation
    title = truncate_field(render_template(title_tmpl, variables), _TITLE_MAX)
    desc = truncate_field(render_template(desc_tmpl, variables), _DESC_MAX)
    footer_text = truncate_field(render_template(footer_tmpl, variables), _FOOTER_MAX)

    fields = []
    if date:
        fields.append({"name": "日期", "value": date, "inline": True})

    payload = {
        "embeds": [
            {
                "title": title,
                "description": desc,
                "color": _EMBED_COLOR,
                "fields": fields,
                "footer": {"text": footer_text},
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.error("Discord Webhook send failed: %s", exc)
