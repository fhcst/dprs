"""Tests for Discord template model fields and template engine (TDD red phase)."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_dc_template")
    from core.users.models import User
    from core.classes.models import Class, ClassMembership
    await init_beanie(database=database, document_models=[User, Class, ClassMembership])
    yield database
    client.close()


@pytest.fixture
async def teacher(db):
    from core.users.models import User
    from core.auth.password import hash_password
    from core.auth.permissions import TEACHER
    u = User(
        username="teach",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(TEACHER),
    )
    await u.insert()
    return u


# ─── Model tests: DiscordTemplate on Class ────────────────────────────────────


async def test_class_discord_template_default_is_none(db, teacher):
    """Creating a Class without setting discord_template yields None."""
    from core.classes.models import Class
    c = Class(
        name="No Template",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="ABCD1234",
    )
    assert c.discord_template is None


async def test_class_discord_template_stores_values(db, teacher):
    """Creating a Class with a DiscordTemplate, saving & reloading preserves values."""
    from core.classes.models import Class, DiscordTemplate
    tpl = DiscordTemplate(
        title_format="{task_name} - {date}",
        description_template="Please complete: {description}",
        footer_text="My Custom Footer",
    )
    c = Class(
        name="With Template",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="TPL12345",
        discord_template=tpl,
    )
    await c.insert()
    fetched = await Class.get(c.id)
    assert fetched.discord_template is not None
    assert fetched.discord_template.title_format == "{task_name} - {date}"
    assert fetched.discord_template.description_template == "Please complete: {description}"
    assert fetched.discord_template.footer_text == "My Custom Footer"


async def test_class_discord_template_backward_compatible(db, teacher):
    """Existing docs without discord_template remain unaffected (field is None)."""
    from core.classes.models import Class
    c = Class(
        name="Legacy Class",
        visibility="public",
        owner_id=str(teacher.id),
        invite_code="LEGACY01",
    )
    await c.insert()
    fetched = await Class.get(c.id)
    assert fetched.discord_template is None


async def test_discord_template_model_defaults():
    """DiscordTemplate default values are empty strings for all three fields."""
    from core.classes.models import DiscordTemplate
    tpl = DiscordTemplate()
    assert tpl.title_format == ""
    assert tpl.description_template == ""
    assert tpl.footer_text == ""


# ─── TDD red-phase tests: template engine functions ───────────────────────────
# These import from integrations.discord.service which does not yet export
# SafeDict, render_template, resolve_template_field, or truncate_field.
# They will fail with ImportError until the implementation is written.


def test_safe_dict_returns_placeholder_for_missing_key():
    """SafeDict replaces known keys and preserves unknown ones as {key}."""
    from integrations.discord.service import SafeDict
    result = "{a} {b}".format_map(SafeDict({"a": "1"}))
    assert result == "1 {b}"


def test_render_template_normal_substitution():
    """render_template replaces all four standard variables correctly."""
    from integrations.discord.service import render_template
    template = "{task_name} | {description} | {date} | {class_name}"
    variables = {
        "task_name": "Daily Practice",
        "description": "Do your exercises",
        "date": "2026-03-25",
        "class_name": "Python 101",
    }
    result = render_template(template, variables)
    assert result == "Daily Practice | Do your exercises | 2026-03-25 | Python 101"


def test_render_template_undefined_variable_preserved():
    """{unknown} placeholders stay as-is in the rendered output."""
    from integrations.discord.service import render_template
    template = "Hello {task_name}, note: {unknown}"
    variables = {"task_name": "Quiz"}
    result = render_template(template, variables)
    assert result == "Hello Quiz, note: {unknown}"


def test_render_template_malformed_braces_fallback():
    """A single '{' in the template returns the original text instead of crashing."""
    from integrations.discord.service import render_template
    template = "Bad template with { only"
    variables = {"task_name": "Quiz"}
    result = render_template(template, variables)
    assert result == template


def test_resolve_template_field_fallback_order():
    """Fallback order: task override > class default > system default."""
    from integrations.discord.service import resolve_template_field
    # Task override wins
    assert resolve_template_field("override", "class_val", "system_val") == "override"
    # Class default used when override is empty
    assert resolve_template_field("", "class_val", "system_val") == "class_val"
    # System default used when both are empty
    assert resolve_template_field("", "", "system_val") == "system_val"


def test_truncate_embed_field():
    """Strings longer than max_length are truncated to (max_length - 3) + '...'."""
    from integrations.discord.service import truncate_field
    long_text = "A" * 300
    result = truncate_field(long_text, 256)
    assert len(result) == 256
    assert result.endswith("...")
    assert result == "A" * 253 + "..."
    # Short strings are returned as-is
    short_text = "Hello"
    assert truncate_field(short_text, 256) == "Hello"
