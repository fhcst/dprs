## 1. 環境判定單一事實來源

- [x] 1.1 建立 `src/shared/environment.py`，提供 `is_production()`，將 `FASTAPI_APP_ENVIRONMENT` 經 `strip()` + 轉小寫後於 `{"prod", "production"}` 內回傳 `True`，其餘（含 `dev`／`development`／`staging`／未設定）回傳 `False`，且於呼叫時讀取環境變數 —— 落實設計決策「is_production() single source of truth」與規格「Single source of truth for production environment detection」。驗證：新增單元測試覆蓋 `prod`／`production`／`PROD` 為 True 與 `dev`／`development`／未設定為 False，以 `.venv/bin/python -m pytest` 通過。
- [x] 1.2 依 `src/shared/__init__.py` 既有 `from .module import name` + `__all__` 慣例匯出 `is_production`（與 `get_session_secret`），使 `from shared import is_production` 可用。驗證：於 REPL／測試 `from shared import is_production, get_session_secret` 不拋 ImportError。
- [x] 1.3 將 `src/core/auth/router.py` 與 `src/pages/router.py` 的 `_is_production()` 改為委派 `is_production()`，並將 `src/shared/sessions.py` send_wrapper 內 inline 判定改用 `is_production()`，使 4 處判定收斂為單一來源 —— 同樣對應「is_production() single source of truth」。驗證：既有 `tests/test_secure_cookie.py` 對 `_is_production()` 的斷言（`production` → True、`staging` → False）仍綠。

## 2. SESSION_SECRET resolver 統一

- [x] 2.1 於 `src/shared/environment.py` 提供 `get_session_secret()`：`SESSION_SECRET` 已設定時回傳之，未設定時回傳 process 內**僅產生一次**的隨機 `secrets.token_hex(32)` 退路，使同一 process 的 JWT 與 SessionMiddleware 取得相同密鑰 —— 落實設計決策「SESSION_SECRET resolver unification」。驗證：單元測試確認設定 env 時回傳該值、未設定時兩次呼叫回傳相同隨機值。
- [x] 2.2 將 `src/core/auth/jwt.py` 的 `create_access_token`／`decode_access_token` 與 `src/main.py` 的 SessionMiddleware 密鑰改用 `get_session_secret()`，取代 `os.getenv("SESSION_SECRET", _DEFAULT_SECRET)` 與 `os.getenv("SESSION_SECRET") or secrets.token_hex(32)`，使簽章與驗證共用同一把密鑰 —— 仍對應「SESSION_SECRET resolver unification」。驗證：以同一 `SESSION_SECRET` 簽出的 JWT 可被 `decode_access_token` 驗證；未設定 env 時 JWT 與 session cookie 使用相同退路密鑰。

## 3. 強化啟動密鑰防護

- [x] 3.1 強化 `src/core/auth/jwt.py` 的 `check_secret_safety()`：對 `get_session_secret()` 解析出的實際密鑰，命中「內含 `_DEFAULT_SECRET`（子字串比對，含以預設值補字元的近預設弱密鑰）／不分大小寫含 `changeme`／長度 ≤ 32」任一即視為不安全；`is_production()` 為 True 時 `raise RuntimeError`（訊息含產生強密鑰指引），否則記 WARNING；簽章改為 `check_secret_safety(secret: str | None = None)` 以利測試 —— 落實設計決策「Weak-secret rejection policy」與規格「JWT secret safety check at startup」。驗證：正式環境對預設值／`changeme_session`／<32 字元 raise、開發環境僅 warn、正式環境對 64-hex 強密鑰不 raise 不 warn。
- [x] 3.2 確認 `src/main.py` lifespan 仍於啟動時呼叫 `check_secret_safety()`，使正式環境弱密鑰會阻止啟動。驗證：以正式環境 + 弱密鑰啟動流程觸發 `RuntimeError`（單元或整合測試）。

## 4. entrypoint 與應用程式判定一致

- [x] 4.1 修改 `scripts/docker-entrypoint.sh` production 分支，使其同時接受 `FASTAPI_APP_ENVIRONMENT` 為 `prod` 與 `production`，與應用程式 `is_production()` 判定一致 —— 落實設計決策「docker-entrypoint.sh environment parity」。驗證：以 `FASTAPI_APP_ENVIRONMENT=production` 與 `=prod` 分別執行 entrypoint 邏輯時皆走 production-server 分支（手動以 shell 帶入變數驗證輸出訊息）。

## 5. 測試

- [x] 5.1 為 `is_production()` 撰寫測試（follow 既有 monkeypatch + reload 模式）：`prod`／`production`／`PROD` 為 True，`dev`／`development`／未設定為 False —— 對應規格「Single source of truth for production environment detection」。驗證：`.venv/bin/python -m pytest` 對應測試通過。
- [x] 5.2 為強化後的 `check_secret_safety()` 撰寫測試：正式環境對預設值、`changeme_session`、<32 字元密鑰 RAISE；開發環境不 raise（warn）；正式環境對 64-hex 強密鑰 PASS —— 對應規格「JWT secret safety check at startup」與設計決策「Weak-secret rejection policy」。驗證：`.venv/bin/python -m pytest` 對應測試通過。
- [x] 5.3 為登入 Secure 旗標撰寫／更新測試：`is_production()` 為 True 時登入回應的 `access_token` cookie 帶 `Secure`、為 False 時不帶 —— 對應規格「Auth cookies use Secure flag in production」。驗證：`.venv/bin/python -m pytest tests/test_secure_cookie.py` 全綠。
- [x] 5.4 更新既有 `tests/test_security_audit.py` 的密鑰測試以配合 resolver 與 `check_secret_safety(secret=...)` 簽章，保留「非正式環境預設值會 warn」的既有行為驗證 —— 對應「SESSION_SECRET resolver unification」。驗證：`.venv/bin/python -m pytest tests/test_security_audit.py` 全綠。
