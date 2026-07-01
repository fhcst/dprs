"""環境判定與 session 密鑰解析的單一事實來源。

集中處理「是否為正式環境」與「實際使用的 SESSION_SECRET」，
讓 JWT 簽章、SessionMiddleware 與 cookie 的 Secure 旗標判定全部收斂到同一處，
避免各模組各自以字面值比對而產生分歧。
"""
import os
import secrets

# 開發用預設密鑰；正式環境若使用此值會被 check_secret_safety() 擋下。
_DEFAULT_SECRET = "dev-secret-change-in-production"

# process 層級僅產生一次的隨機退路密鑰。未設定 SESSION_SECRET 時，
# 同一 process 內的 JWT 與 SessionMiddleware 都會取得這把相同的退路密鑰，
# 而非各自隨機，藉此消除 main.py 與 jwt.py 之間的密鑰分歧。
_FALLBACK_SECRET = secrets.token_hex(32)

# 視為正式環境的關鍵字（已正規化為小寫）。
_PRODUCTION_VALUES = frozenset({"prod", "production"})


def is_production() -> bool:
    """判定目前是否為正式環境部署。

    於**呼叫時**讀取 ``FASTAPI_APP_ENVIRONMENT``，將其去頭尾空白並轉小寫後，
    若落在 ``{"prod", "production"}`` 內即回傳 ``True``；其餘值
    （含 ``dev``、``development``、``staging`` 與未設定）一律回傳 ``False``。

    於呼叫時讀取環境變數，方便測試以 ``monkeypatch`` 覆寫 ``os.environ``。
    """
    raw = os.getenv("FASTAPI_APP_ENVIRONMENT", "")
    return raw.strip().lower() in _PRODUCTION_VALUES


def get_session_secret() -> str:
    """解析實際使用的 session 密鑰，作為 JWT 與 SessionMiddleware 的單一來源。

    ``SESSION_SECRET`` 已設定時回傳該值；未設定時回傳 process 內僅產生一次的
    隨機退路密鑰，確保同一 process 的所有消費者（JWT 簽章／驗證、
    SessionMiddleware）取得相同密鑰。於呼叫時讀取環境變數以利測試覆寫。
    """
    env = os.getenv("SESSION_SECRET")
    return env if env else _FALLBACK_SECRET
