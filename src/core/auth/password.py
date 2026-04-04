"""Password hashing utilities using argon2-cffi (Argon2id)."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against an Argon2id hash."""
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def validate_password_strength(plain: str) -> None:
    """Raise ValueError if the password does not meet strength requirements.

    Requirements:
    - Minimum 8 characters.
    """
    if len(plain) < 8:
        raise ValueError("密碼長度至少需要 8 個字元。")
