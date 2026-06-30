from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

import jwt
from fastapi import FastAPI
from fastapi.requests import HTTPConnection
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from starlette.datastructures import MutableHeaders
from starlette.types import Message, Receive, Scope, Send

from shared.environment import is_production


# 建議將時間處理統一，這裡示範使用 UTC (標準作法) 或 UTC+8
def get_now() -> datetime:
    """
    獲取當前時間。

    Returns:
        datetime: 當前時間，設定為 UTC+8 時區。

    範例:
        >>> now = get_now()
        >>> print(now)
        2023-10-27 10:00:00+08:00
    """
    # 如果需要 UTC+8，請保留原本的 timezone 設定
    return datetime.now(timezone(timedelta(hours=8)))


class SessionMiddleware:
    """
    用於處理 Session 的 Middleware，使用 JWT 儲存在 Cookie 中。

    這個 Middleware 會攔截請求，檢查 Cookie 中的 Session Token (JWT)，
    並將解碼後的 Session 資料放入 `scope['session']` 中。
    在回應時，它會將 `scope['session']` 中的資料重新編碼為 JWT 並寫入 Cookie。

    範例:
        >>> from fastapi import FastAPI
        >>> from src.shared.sessions import SessionMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(
        >>>     SessionMiddleware,
        >>>     secret_key="your-secret-key",
        >>>     session_cookie="my-session",
        >>>     max_age=3600
        >>> )
    """
    def __init__(
        self,
        app: FastAPI,
        secret_key: str,  # 建議必填，不要設預設值以免誤用
        session_cookie: str = "session",
        max_age: Optional[int] = 24 * 60 * 60,  # 1 day
        path: str = "/",
        same_site: Literal["lax", "strict", "none"] = "lax",
        session_struct: type = dict,
        default_session: Optional[Dict[str, Any]] = None,  # 新增：可自訂預設 session
    ) -> None:
        """
        初始化 SessionMiddleware。

        Args:
            app (FastAPI): FastAPI 應用程式實例。
            secret_key (str): 用於簽署 JWT 的密鑰。
            session_cookie (str, optional): Session Cookie 的名稱。預設為 "session"。
            max_age (int, optional): Session Cookie 的過期時間（秒）。預設為 1 天。
            path (str, optional): Cookie 的路徑。預設為 "/"。
            same_site (Literal["lax", "strict", "none"], optional): Cookie 的 SameSite 屬性。預設為 "lax"。
            session_struct (type, optional): Session 資料的結構型別（例如 Pydantic model 或 dict）。預設為 dict。
            default_session (Optional[Dict[str, Any]], optional): 預設的 Session 資料。預設為 None (即空字典)。
        """
        self._app = app
        self._secret_key = secret_key
        self._session_cookie = session_cookie
        self._max_age = max_age
        self._path = path
        self.security_flags = f"httponly; samesite={same_site}"
        self._session_struct = session_struct
        self._default_session = default_session if default_session else {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self._session_cookie in connection.cookies:
            jwt_token = connection.cookies[self._session_cookie]
            try:
                # 使用 algorithms 關鍵字參數 (Fix V1 issue)
                data = jwt.decode(jwt_token, self._secret_key, algorithms=["HS256"])

                # 處理 Pydantic 轉換
                if self._session_struct is not dict:
                    session_obj = self._session_struct(**data)
                else:
                    session_obj = data

                scope["session"] = session_obj
                initial_session_was_empty = False
            except (InvalidTokenError, ExpiredSignatureError):
                if self._session_struct is not dict:
                    scope["session"] = self._session_struct(**self._default_session)
                else:
                    scope["session"] = self._default_session.copy()
        else:
            if self._session_struct is not dict:
                scope["session"] = self._session_struct(**self._default_session)
            else:
                scope["session"] = self._default_session.copy()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                # 於回應時透過共用 is_production() 判定（呼叫時讀取環境變數，
                # 同時接受 prod 與 production），確保 session cookie 的 Secure
                # 旗標與其他端點一致。
                security_flags = self.security_flags + ("; secure" if is_production() else "")

                if scope.get("session"):
                    # 1. 轉換為 dict
                    if hasattr(scope["session"], "model_dump"):
                        session_data = scope["session"].model_dump()
                    elif hasattr(scope["session"], "dict"):  # 相容 Pydantic v1
                        session_data = scope["session"].dict()
                    else:
                        session_data = dict(scope["session"])

                    # 2. 設定過期時間 (Fix V1 Bug: 修改 copy 而非原始物件)
                    if "exp" not in session_data and self._max_age:
                        now = get_now()
                        expire_time = now + timedelta(seconds=self._max_age)
                        session_data["exp"] = int(
                            expire_time.timestamp()
                        )  # JWT 標準是 timestamp

                    # 3. Encode
                    data = jwt.encode(session_data, self._secret_key, algorithm="HS256")

                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(
                        session_cookie=self._session_cookie,
                        data=data,
                        path=self._path,
                        max_age=f"Max-Age={self._max_age}; " if self._max_age else "",
                        security_flags=security_flags,
                    )
                    headers.append("Set-Cookie", header_value)

                elif not initial_session_was_empty:
                    # Session 被清空，刪除 Cookie
                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(
                        session_cookie=self._session_cookie,
                        data="null",
                        path=self._path,
                        expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
                        security_flags=security_flags,
                    )
                    headers.append("Set-Cookie", header_value)

            await send(message)

        await self._app(scope, receive, send_wrapper)
