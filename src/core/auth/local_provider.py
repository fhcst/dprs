"""LocalAuthProvider — username/password authentication."""
from typing import Any

from core.auth.password import verify_password
from core.users.models import User

# Pre-computed Argon2id hash used for the dummy verify call when a username is
# not found.  This ensures the user-not-found code path takes ~the same wall
# clock time as the wrong-password path, eliminating the timing side-channel
# described in CWE-208.  The value below was generated with:
#   PasswordHasher().hash("dummy_placeholder_not_a_real_password_12345")
# It is intentionally hard-coded so module import is O(1) and the hash is
# never None/empty (which would let Argon2id short-circuit and defeat the fix).
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$VwIdRDTRLIbZZWEucTXlBw$5+qn4371yFK+uvjoq5FdkPg1GxTausWcspwwPfpMb6A"


class LocalAuthProvider:
    """Default AuthProvider using username + password stored in MongoDB."""

    async def authenticate(self, credentials: dict[str, Any]) -> User:
        """
        Authenticate using username and password.

        Raises:
            ValueError: If username not found or password is wrong.
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        user = await User.find_one(User.username == username)
        if user is None:
            # Perform a dummy Argon2id verify to consume the same ~40-50 ms
            # as the real verify below, preventing a timing side-channel that
            # would allow an attacker to enumerate valid usernames (CWE-208).
            verify_password("dummy_placeholder_not_a_real_password_12345", DUMMY_HASH)
            raise ValueError("Invalid username or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid username or password")

        if not user.is_active:
            raise ValueError("Account is disabled")

        return user
