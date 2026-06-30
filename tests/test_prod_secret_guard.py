"""Tests for the production-secret guard hardening (change: harden-prod-secret-guard).

Covers:
- shared.environment.is_production() truth table (single source of truth).
- shared.environment.get_session_secret() resolver (env value vs process-stable fallback).
- core.auth.jwt.check_secret_safety() weak-secret policy: raises in production,
  warns in non-production, passes for a strong 64-hex secret.
- JWT sign/verify round-trip uses the SAME resolved secret.

The helpers read environment variables at call time, so tests use monkeypatch on
os.environ rather than module reloads.
"""
import logging
import secrets

import pytest


# ---------------------------------------------------------------------------
# is_production() truth table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["prod", "production", "PROD", "  production  ", "Prod"])
def test_is_production_true_values(monkeypatch, value):
    """prod / production (any case, surrounding whitespace) are production."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", value)
    from shared.environment import is_production
    assert is_production() is True


@pytest.mark.parametrize("value", ["dev", "development", "staging", "test", ""])
def test_is_production_false_values(monkeypatch, value):
    """Everything other than prod/production is non-production."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", value)
    from shared.environment import is_production
    assert is_production() is False


def test_is_production_false_when_unset(monkeypatch):
    """An unset FASTAPI_APP_ENVIRONMENT is non-production."""
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    from shared.environment import is_production
    assert is_production() is False


def test_is_production_importable_from_package(monkeypatch):
    """is_production is re-exported from the shared package (no ImportError)."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from shared import is_production
    assert is_production() is True


# ---------------------------------------------------------------------------
# get_session_secret() resolver
# ---------------------------------------------------------------------------

def test_get_session_secret_returns_env_value(monkeypatch):
    """When SESSION_SECRET is set, the resolver returns exactly that value."""
    monkeypatch.setenv("SESSION_SECRET", "my-explicit-production-secret-value-1234567890")
    from shared.environment import get_session_secret
    assert get_session_secret() == "my-explicit-production-secret-value-1234567890"


def test_get_session_secret_fallback_is_process_stable(monkeypatch):
    """Without SESSION_SECRET, two calls return the SAME random fallback."""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    from shared.environment import get_session_secret
    first = get_session_secret()
    second = get_session_secret()
    assert first == second
    assert len(first) == 64  # secrets.token_hex(32)
    # NOTE: this only checks the resolver agrees with itself. That the SAME fallback is
    # what JWT signing actually uses (cross-consumer stability) is verified by
    # test_jwt_fallback_secret_matches_resolver below.


def test_get_session_secret_importable_from_package():
    """get_session_secret is re-exported from the shared package (no ImportError)."""
    from shared import get_session_secret
    assert callable(get_session_secret)


# ---------------------------------------------------------------------------
# check_secret_safety() — production raises on weak secrets
# ---------------------------------------------------------------------------

def test_check_secret_safety_raises_in_production_for_default(monkeypatch):
    """Production + default development secret -> RuntimeError."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    from shared.environment import _DEFAULT_SECRET
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=_DEFAULT_SECRET)


def test_check_secret_safety_raises_in_production_for_changeme_via_resolver(monkeypatch):
    """Production (env='prod') + SESSION_SECRET='changeme_session' -> RuntimeError.

    Exercises both the load-bearing 'prod' value and the published .env.example secret
    through the real resolver path (no explicit secret argument).
    """
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "prod")
    monkeypatch.setenv("SESSION_SECRET", "changeme_session")
    from core.auth.jwt import check_secret_safety
    with pytest.raises(RuntimeError):
        check_secret_safety()


def test_check_secret_safety_raises_for_long_changeme_via_resolver(monkeypatch):
    """Production + a >32-char SESSION_SECRET containing 'changeme', NO explicit arg.

    Exercises the 'changeme' branch in ISOLATION through the real resolver path: the
    secret is long enough (> 32 chars) that the length check does NOT fire, and it does
    NOT embed the default value, so the RuntimeError can only come from the changeme
    branch. Unlike the short 'changeme_session' case (which also trips the length check),
    this test would fail if the changeme detection were accidentally removed.
    """
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    long_changeme = "changeme_this_is_now_long_enough_yes_ok_123"
    assert len(long_changeme) > 32
    monkeypatch.setenv("SESSION_SECRET", long_changeme)
    from core.auth.jwt import check_secret_safety
    with pytest.raises(RuntimeError):
        check_secret_safety()  # resolver path, no explicit secret=


def test_check_secret_safety_raises_in_production_for_changeme_uppercase(monkeypatch):
    """The changeme check is case-insensitive."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    with pytest.raises(RuntimeError):
        check_secret_safety(secret="ChangeMe_Now_Please_With_Padding_xx")


def test_check_secret_safety_raises_in_production_for_short_secret(monkeypatch):
    """Production + a secret shorter than 32 chars -> RuntimeError."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    short_secret = "a" * 31  # 31 < 32
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=short_secret)


def test_check_secret_safety_raises_in_production_for_at_boundary_secret(monkeypatch):
    """Production + an exactly-32-char secret -> RuntimeError.

    Regression guard for the off-by-one boundary: the length policy uses '<= 32'
    (not '< 32'), so a near-default 32-char value such as
    'dev-secret-change-in-production!' (the default padded with one char) or a
    trivial 'a' * 32 is rejected rather than slipping through.
    """
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    boundary_secret = "a" * 32  # exactly 32 -> still weak
    assert len(boundary_secret) == 32
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=boundary_secret)
    # The documented default padded to exactly 32 chars must also be rejected.
    padded_default = "dev-secret-change-in-production!"  # 32 chars
    assert len(padded_default) == 32
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=padded_default)


def test_check_secret_safety_raises_in_production_for_padded_default_over_boundary(monkeypatch):
    """Production + the default padded PAST the 32-char boundary -> RuntimeError.

    Regression guard for the padded-default bypass: a value such as
    'dev-secret-change-in-production!!' (33 chars) exceeds the length threshold
    (33 > 32) and is NOT string-equal to the default, so it would slip through a
    naive '== _DEFAULT_SECRET' check. The policy uses substring containment of the
    default, so any value embedding the default is still rejected regardless of length.
    """
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    from shared.environment import _DEFAULT_SECRET
    padded_default = _DEFAULT_SECRET + "!!"  # 33 chars, > 32
    assert len(padded_default) > 32
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=padded_default)
    # A longer padded variant is likewise rejected.
    long_padded = _DEFAULT_SECRET + "-and-some-more-padding-xxxxxxxxxx"
    assert len(long_padded) > 32
    with pytest.raises(RuntimeError):
        check_secret_safety(secret=long_padded)


def test_check_secret_safety_passes_in_production_for_strong_secret(monkeypatch, caplog):
    """Production + a strong 64-hex secret -> no raise and no warning."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "production")
    from core.auth.jwt import check_secret_safety
    strong_secret = secrets.token_hex(32)  # 64 hex chars
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        check_secret_safety(secret=strong_secret)  # must not raise
    assert caplog.records == []


# ---------------------------------------------------------------------------
# check_secret_safety() — non-production warns (never raises)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "weak_secret",
    [
        "dev-secret-change-in-production",  # default
        "changeme_session",                 # contains changeme
        "tooshort",                          # < 32 chars
    ],
)
def test_check_secret_safety_warns_in_dev_for_weak_secret(monkeypatch, caplog, weak_secret):
    """Non-production + weak secret -> WARNING log, never RuntimeError."""
    monkeypatch.setenv("FASTAPI_APP_ENVIRONMENT", "development")
    from core.auth.jwt import check_secret_safety
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        check_secret_safety(secret=weak_secret)  # must not raise
    assert any("SESSION_SECRET" in r.message for r in caplog.records)


def test_check_secret_safety_does_not_warn_in_dev_for_strong_secret(monkeypatch, caplog):
    """Non-production + strong secret -> no warning."""
    monkeypatch.delenv("FASTAPI_APP_ENVIRONMENT", raising=False)
    from core.auth.jwt import check_secret_safety
    with caplog.at_level(logging.WARNING, logger="core.auth.jwt"):
        check_secret_safety(secret=secrets.token_hex(32))
    assert caplog.records == []


# ---------------------------------------------------------------------------
# JWT sign/verify uses the SAME resolved secret
# ---------------------------------------------------------------------------

def test_jwt_roundtrip_with_explicit_secret(monkeypatch):
    """A token signed with the resolved secret verifies with the same resolver."""
    monkeypatch.setenv("SESSION_SECRET", secrets.token_hex(32))
    from core.auth.jwt import create_access_token, decode_access_token
    token = create_access_token(user_id="user-1", permissions=7)
    decoded = decode_access_token(token)
    assert decoded["user_id"] == "user-1"
    assert decoded["permissions"] == 7


def test_jwt_roundtrip_with_fallback_secret(monkeypatch):
    """With SESSION_SECRET unset, sign and verify share the process-stable fallback."""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    from core.auth.jwt import create_access_token, decode_access_token
    token = create_access_token(user_id="user-2", permissions=3)
    decoded = decode_access_token(token)
    assert decoded["user_id"] == "user-2"
    assert decoded["permissions"] == 3


def test_jwt_fallback_secret_matches_resolver(monkeypatch):
    """The fallback secret used to SIGN a JWT is EXACTLY what get_session_secret() returns.

    Cross-consumer stability check: with SESSION_SECRET unset, a token signed by
    create_access_token() (which signs with the process-stable fallback) must decode
    using the value returned by get_session_secret() directly. This proves the JWT
    signer and every other consumer (e.g. SessionMiddleware's secret_key) share the
    same fallback, rather than only asserting two consecutive resolver calls match.
    """
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    import jwt as pyjwt
    from core.auth.jwt import _ALGORITHM, create_access_token
    from shared.environment import get_session_secret
    token = create_access_token(user_id="user-3", permissions=5)
    # Decode with the resolver's value directly (not via decode_access_token) to assert
    # equality of the signing secret and the resolver output.
    decoded = pyjwt.decode(token, get_session_secret(), algorithms=[_ALGORITHM])
    assert decoded["user_id"] == "user-3"
    assert decoded["permissions"] == 5
