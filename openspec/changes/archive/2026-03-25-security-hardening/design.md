## Context

JWT 預設密鑰在 `check_secret_safety()` 中定義但從未在啟動流程中被呼叫、auth cookie 和 session cookie 缺少 `secure=True` 旗標、login/password/setup 端點無速率限制、form-based POST 端點無 CSRF 防護、Docker 基礎設施中 MongoDB/Redis 無認證且 mongo-express 使用預設帳密。

## Goals / Non-Goals

**Goals:**

- 修復 5 項安全審計發現（R2–R6），確保部署環境安全
- JWT 啟動檢查在生產環境強制執行
- 所有認證 cookie 在 production 環境設定 Secure flag
- 關鍵端點加入速率限制以防暴力破解
- form-based POST 加入 CSRF 防護
- Docker infrastructure 加入基本認證

**Non-Goals:**

- 不改變認證架構或 token 格式
- 不改變現有的 permission/guard 機制
- 不新增完整的 WAF 或 IDS 系統

## Decisions

### JWT startup check: 呼叫 `check_secret_safety()` 並在 prod 環境 raise

在 `src/main.py` 的 lifespan 啟動階段呼叫 `check_secret_safety()`。當 `FASTAPI_APP_ENVIRONMENT` 為 `production` 且偵測到預設密鑰時，raise `RuntimeError` 終止啟動。這比先前僅 log WARNING 的做法更嚴格，確保生產環境不會使用預設密鑰。

替代方案：維持 WARNING-only。缺點是生產環境可能因疏忽而使用預設密鑰。

### Cookie secure: 依 `FASTAPI_APP_ENVIRONMENT` 判斷是否設定 `secure=True`

在所有 `set_cookie` 呼叫（`src/core/auth/router.py`、`src/pages/router.py`）及 session cookie（`src/shared/sessions.py`）中，根據 `FASTAPI_APP_ENVIRONMENT` 環境變數判斷是否加入 `secure=True`。開發環境（非 production）不設定 Secure 以允許 HTTP localhost 測試。

替代方案：永遠設定 `secure=True`。缺點是 localhost 開發無法使用 HTTP。

### Rate limit: 使用 slowapi（基於 limits），對關鍵端點設限

整合 slowapi library，在 `src/main.py` 加入 `SlowAPI` middleware。對以下端點加入速率限制 decorator：
- `POST /auth/login` — 防止暴力破解
- `POST /pages/login` — 防止暴力破解（form login）
- `POST /auth/change-password` — 防止密碼猜測
- `POST /setup` — 防止 setup wizard 被濫用

替代方案：使用 Redis-based 自訂 rate limiter。缺點是需要額外維護，slowapi 是成熟且廣泛使用的方案。

### CSRF: 使用 SameSite=Lax + 對 form-based POST 加入 Origin/Referer 檢查

採用輕量方案：依賴 cookie 的 `SameSite=Lax` 屬性（瀏覽器預設行為），再對 form-based POST 端點加入 Origin/Referer header 檢查作為額外防護層。不需要額外 library。

替代方案：使用 starlette-csrf 或 double-submit cookie pattern。缺點是增加依賴或需要在每個 form 中注入 token。

### Docker: 加入 MongoDB/Redis 認證，bind ports to 127.0.0.1

- MongoDB: 加入 `MONGO_INITDB_ROOT_USERNAME` 和 `MONGO_INITDB_ROOT_PASSWORD` 環境變數，更新 app 的 `MONGO_URL` 連線字串
- Redis: 加入 `--requirepass` 啟動參數，更新 app 的 Redis 連線設定
- 將 MongoDB 和 Redis 的 port binding 限制為 `127.0.0.1`
- 移除 mongo-express 或改為 disabled-by-default（使用 profile）

替代方案：使用 Docker network isolation only。缺點是不防護同機器的其他服務存取。

## Risks / Trade-offs

- [slowapi 新增依賴] → slowapi 是成熟且輕量的 library，維護負擔低
- [CSRF Origin 檢查可能影響某些 proxy 環境] → 可透過設定允許的 Origin 列表解決
- [Docker 認證需要更新部署文件] → 在 `.env.example` 或 README 中加入說明
- [生產環境 JWT 硬性阻擋可能影響首次部署] → 錯誤訊息需清楚說明如何設定環境變數
