"""JWT token creation and decoding."""
import logging
import os
from datetime import datetime, timedelta, timezone

import jwt

from shared.environment import _DEFAULT_SECRET, get_session_secret, is_production

_ALGORITHM = "HS256"
_DEFAULT_EXPIRES = int(os.getenv("JWT_EXPIRES_SECONDS", str(60 * 60 * 24)))  # 24h

# 弱密鑰判定門檻：真正的 secrets.token_hex(32) 會是 64 個十六進位字元，遠超此門檻。
# 判定採「不超過」（<=）而非「短於」（<），使剛好 32 字元的近預設弱密鑰
# （例如預設值補一個字元的 'dev-secret-change-in-production!'）也會被擋下。
_MIN_SECRET_LENGTH = 32

_logger = logging.getLogger(__name__)


def _is_secret_insecure(secret: str) -> bool:
    """回傳密鑰是否命中弱密鑰政策。

    命中以下任一條件即視為不安全：
    - 內含開發預設值 ``_DEFAULT_SECRET``（採子字串比對，不只比相等；如此一來
      以預設值補上任意數量字元的近預設弱密鑰——例如 33 字元的
      ``dev-secret-change-in-production!!``——同樣會被擋下，而非僅擋下剛好相等
      或剛好 32 字元的情形）。
    - 不分大小寫含有子字串 ``changeme``（涵蓋 ``.env.example`` 的 ``changeme_session``）。
    - 長度不超過 ``_MIN_SECRET_LENGTH`` 字元（即 32 字元以下，含剛好 32 字元）。
    """
    return (
        _DEFAULT_SECRET in secret
        or "changeme" in secret.lower()
        or len(secret) <= _MIN_SECRET_LENGTH
    )


def check_secret_safety(secret: str | None = None) -> None:
    """檢查實際使用的 session 密鑰是否安全，正式環境弱密鑰即阻止啟動。

    密鑰透過共用 resolver 解析（與 JWT 簽章、SessionMiddleware 同一把），
    再以弱密鑰政策檢查（內含預設值／含 ``changeme``／長度不超過 32 字元）。
    ``is_production()`` 為 ``True`` 時對弱密鑰 ``raise RuntimeError`` 阻止啟動；
    其餘環境僅記錄 WARNING，不阻擋啟動。

    Args:
        secret: 省略（``None``）時解析為實際使用的密鑰；傳入字串時直接驗證該值，
            方便在不更動環境狀態的情況下測試弱密鑰政策。
    """
    resolved = secret if secret is not None else get_session_secret()

    if not _is_secret_insecure(resolved):
        return

    if is_production():
        raise RuntimeError(
            "SESSION_SECRET 不安全：內含開發預設值、含有 changeme，或長度不超過 32 字元。"
            "正式環境必須改用強隨機密鑰，請執行 "
            "`python -c \"import secrets; print(secrets.token_hex(32))\"` "
            "產生後設定為 SESSION_SECRET 再重新啟動。"
        )

    _logger.warning(
        "SESSION_SECRET 不安全：等於開發預設值、含有 changeme，或長度不超過 32 字元。"
        "部署到正式環境前務必改為強隨機密鑰。"
    )


def create_access_token(
    user_id: str,
    permissions: int,
    expires_seconds: int | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: The user's MongoDB ID as a string.
        permissions: The user's permission flags as an integer.
        expires_seconds: Token lifetime in seconds. Defaults to JWT_EXPIRES_SECONDS env var.

    Returns:
        A signed JWT string.
    """
    if expires_seconds is None:
        expires_seconds = _DEFAULT_EXPIRES

    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "permissions": permissions,
        "iat": now,
        "exp": now + timedelta(seconds=expires_seconds),
    }
    return jwt.encode(payload, get_session_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid or tampered.
    """
    return jwt.decode(token, get_session_secret(), algorithms=[_ALGORITHM])
