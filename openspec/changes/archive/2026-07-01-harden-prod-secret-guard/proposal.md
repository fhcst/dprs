## Why

正式部署文件（`scripts/docker-entrypoint.sh`、`.env.example`、`docker-compose.yml`）一律使用 `FASTAPI_APP_ENVIRONMENT=prod`，但應用程式有 4 處直接拿環境變數和字面值 `"production"` 比對。`"prod" != "production"`，導致按照文件部署的正式環境會**靜默關閉** Secure cookie 與預設密鑰啟動防護，這是承載整個 bug 的關鍵錯誤。此外 `check_secret_safety()` 只擋得住唯一一個字串 `dev-secret-change-in-production`，卻擋不住公開 repo 的 `.env.example` 內 `SESSION_SECRET=changeme_session`；而 `src/main.py` 與 `src/core/auth/jwt.py` 對未設定 `SESSION_SECRET` 時的退路又彼此不一致（一個隨機、一個固定預設字串），使 JWT 簽章與 SessionMiddleware 可能用到不同密鑰。

## What Changes

- 新增單一事實來源 `is_production()`（建議置於新檔 `src/shared/environment.py`，並依 `src/shared/__init__.py` 既有 export 慣例匯出）。將 `FASTAPI_APP_ENVIRONMENT` 經 `strip()` + 轉小寫後，於 `{"prod", "production"}` 內即視為正式環境；`dev`／`development`／未設定皆回傳 `False`（行為不退步）。
- **BREAKING（部署語意修正）**：以 `is_production()` 取代 4 處 inline 比對 —— `src/core/auth/jwt.py`（`check_secret_safety`）、`src/core/auth/router.py:30`（`_is_production`）、`src/pages/router.py:26`（`_is_production`）、`src/shared/sessions.py:119`（inline `is_production`）。按文件以 `prod` 部署者，Secure cookie 與密鑰防護將如預期啟用。
- 修改 `scripts/docker-entrypoint.sh`：production-server 分支同時接受 `prod` 與 `production`，使 entrypoint 與應用程式判定一致。
- 強化 `check_secret_safety()`：密鑰若等於開發預設值、或（不分大小寫）含有 `changeme`、或長度短於 32 字元即視為不安全。正式環境 `raise RuntimeError` 並附帶可行動的訊息；其他環境僅記錄 warning。保持可被 import 與測試。
- 統一 `SESSION_SECRET` 退路：集中以單一 resolver 解析「實際使用的密鑰」，讓 JWT 簽章與 SessionMiddleware 共用同一把密鑰，且 `check_secret_safety()` 驗證的正是這把密鑰；開發環境保留隨機退路的便利性。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `user-auth`: 新增環境正規化的單一事實來源、強化弱密鑰判定（預設值／`changeme`／短於 32 字元），並在正式環境強制阻擋啟動；Secure cookie 的正式環境判定改為同時接受 `prod` 與 `production`。

## Impact

- Affected specs: `user-auth`
- Affected code:
  - `src/shared/environment.py` — 新增 `is_production()` 與 `SESSION_SECRET` resolver（單一事實來源）
  - `src/shared/__init__.py` — 依既有慣例匯出新 helper
  - `src/core/auth/jwt.py` — `check_secret_safety()` 強化、改用共用 resolver 與 `is_production()`
  - `src/core/auth/router.py` — `_is_production()` 改委派至共用 helper
  - `src/pages/router.py` — `_is_production()` 改委派至共用 helper
  - `src/shared/sessions.py` — inline 環境判定改用 `is_production()`
  - `src/main.py` — SessionMiddleware 密鑰改用共用 resolver
  - `scripts/docker-entrypoint.sh` — production 分支同時接受 `prod` 與 `production`
- Affected tests:
  - `tests/test_secure_cookie.py`、`tests/test_security_audit.py` — 既有測試需配合 helper 委派與強化後的 `check_secret_safety()` 行為
  - 新增 `is_production()`、`check_secret_safety()`、Secure cookie 旗標的測試（見 tasks.md）
