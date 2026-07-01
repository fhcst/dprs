"""Tests for the user-auth capability."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_auth")
    from core.users.models import User
    await init_beanie(database=database, document_models=[User])
    yield database
    client.close()


# --- User model ---

async def test_user_model_has_required_fields(db):
    from core.users.models import User
    from core.auth.permissions import STUDENT
    u = User(
        username="alice",
        hashed_password="hashed",
        display_name="Alice",
        permissions=int(STUDENT),
    )
    assert u.username == "alice"
    assert u.permissions == int(STUDENT)
    assert u.created_at is not None
    assert u.tags == []


# --- LocalAuthProvider ---

async def test_local_auth_provider_authenticates_valid_user(db):
    from core.users.models import User
    from core.auth.local_provider import LocalAuthProvider
    from core.auth.password import hash_password
    from core.auth.permissions import STUDENT

    user = User(
        username="bob",
        hashed_password=hash_password("secret123"),
        display_name="Bob",
        permissions=int(STUDENT),
    )
    await user.insert()

    provider = LocalAuthProvider()
    result = await provider.authenticate({"username": "bob", "password": "secret123"})
    assert result is not None
    assert result.username == "bob"
    assert hasattr(result, "permissions")
    assert result.permissions == int(STUDENT)


async def test_local_auth_provider_rejects_wrong_password(db):
    from core.users.models import User
    from core.auth.local_provider import LocalAuthProvider
    from core.auth.password import hash_password

    user = User(
        username="carol",
        hashed_password=hash_password("correct"),
        display_name="Carol",
    )
    await user.insert()

    provider = LocalAuthProvider()
    with pytest.raises(ValueError):
        await provider.authenticate({"username": "carol", "password": "wrong"})


async def test_local_auth_provider_rejects_unknown_user(db):
    from core.auth.local_provider import LocalAuthProvider

    provider = LocalAuthProvider()
    with pytest.raises(ValueError):
        await provider.authenticate({"username": "nobody", "password": "x"})


# --- LocalAuthProvider timing side-channel (CWE-208) ---

def test_local_provider_has_dummy_hash_constant():
    """DUMMY_HASH must exist as a module-level Argon2id hash (not empty/placeholder)."""
    import core.auth.local_provider as lp
    assert hasattr(lp, "DUMMY_HASH"), "local_provider must expose a DUMMY_HASH constant"
    dummy_hash = lp.DUMMY_HASH
    assert isinstance(dummy_hash, str), "DUMMY_HASH must be a string"
    assert len(dummy_hash) > 20, "DUMMY_HASH must be a real Argon2id hash, not empty"
    assert dummy_hash.startswith("$argon2id$"), "DUMMY_HASH must be a valid Argon2id hash (starts with $argon2id$)"


async def test_local_provider_unknown_user_exercises_dummy_hash(db):
    """Authenticating an unknown username must invoke verify_password (via DUMMY_HASH),
    not short-circuit — confirmed by patching verify_password and checking it is called."""
    from unittest.mock import patch, MagicMock
    from core.auth.local_provider import LocalAuthProvider

    mock_verify = MagicMock(return_value=False)
    with patch("core.auth.local_provider.verify_password", mock_verify):
        provider = LocalAuthProvider()
        with pytest.raises(ValueError):
            await provider.authenticate({"username": "ghost_user_does_not_exist", "password": "x"})

    assert mock_verify.called, (
        "verify_password must be called even when the user does not exist "
        "(dummy bcrypt call to prevent timing side-channel)"
    )


# --- JWT token ---

def test_create_token_contains_claims():
    from core.auth.jwt import create_access_token, decode_access_token
    from core.auth.permissions import TEACHER
    token = create_access_token(user_id="user123", permissions=int(TEACHER))
    payload = decode_access_token(token)
    assert payload["user_id"] == "user123"
    assert payload["permissions"] == int(TEACHER)
    assert "exp" in payload


def test_expired_token_raises():
    from core.auth.jwt import create_access_token, decode_access_token
    token = create_access_token(user_id="x", permissions=0, expires_seconds=-1)
    with pytest.raises(Exception):  # jwt.ExpiredSignatureError
        decode_access_token(token)


def test_tampered_token_raises():
    from core.auth.jwt import create_access_token, decode_access_token
    token = create_access_token(user_id="x", permissions=0)
    tampered = token + "tampered"
    with pytest.raises(Exception):
        decode_access_token(tampered)


# --- Password hashing ---

def test_password_hash_uses_argon2id_format():
    from core.auth.password import hash_password
    h = hash_password("mypassword")
    assert h.startswith("$argon2id$"), f"Expected Argon2id hash, got: {h[:20]}"


def test_password_hashing_is_not_plaintext():
    from core.auth.password import hash_password
    h = hash_password("mypassword")
    assert h != "mypassword"
    assert len(h) > 20


def test_password_verify_correct():
    from core.auth.password import hash_password, verify_password
    h = hash_password("mypassword")
    assert verify_password("mypassword", h) is True


def test_password_verify_wrong():
    from core.auth.password import hash_password, verify_password
    h = hash_password("mypassword")
    assert verify_password("wrongpassword", h) is False


# --- Permission-based access control ---

async def test_require_permission_allows_user_with_flag(db):
    from core.auth.guards import require_permission
    from core.auth.permissions import MANAGE_OWN_CLASS as MANAGE_CLASS
    from core.users.models import User
    from core.auth.password import hash_password

    teacher = User(
        username="teach1",
        hashed_password=hash_password("pw"),
        display_name="Teacher",
        permissions=int(MANAGE_CLASS),
    )
    await teacher.insert()

    dep = require_permission(MANAGE_CLASS)
    result = await dep(current_user=teacher)
    assert result.permissions & MANAGE_CLASS


async def test_require_permission_rejects_user_without_flag(db):
    from core.auth.guards import require_permission
    from core.auth.permissions import MANAGE_OWN_CLASS as MANAGE_CLASS, SUBMIT_TASK
    from core.users.models import User
    from core.auth.password import hash_password
    from fastapi import HTTPException

    student = User(
        username="stu1",
        hashed_password=hash_password("pw"),
        display_name="Student",
        permissions=int(SUBMIT_TASK),  # no MANAGE_CLASS
    )

    dep = require_permission(MANAGE_CLASS)
    with pytest.raises(HTTPException) as exc_info:
        await dep(current_user=student)
    assert exc_info.value.status_code == 403


# --- Password strength validation ---

def test_validate_password_strength_rejects_short_password():
    from core.auth.password import validate_password_strength
    with pytest.raises(ValueError, match="8"):
        validate_password_strength("short")


def test_validate_password_strength_rejects_empty():
    from core.auth.password import validate_password_strength
    with pytest.raises(ValueError):
        validate_password_strength("")


def test_validate_password_strength_accepts_exactly_8_chars():
    from core.auth.password import validate_password_strength
    validate_password_strength("exactly8")  # must not raise


def test_validate_password_strength_accepts_long_password():
    from core.auth.password import validate_password_strength
    validate_password_strength("this_is_a_very_long_password_123")  # must not raise
