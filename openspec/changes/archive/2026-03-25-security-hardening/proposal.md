## Summary

安全強化措施：修復 JWT 密鑰啟動檢查、Cookie Secure 旗標、新增速率限制、CSRF 防護、Docker 基礎設施安全。

## Motivation

Security audit 發現多項部署安全問題（CWE-798, CWE-614, CWE-307, CWE-352, CWE-16）。這些問題在上線前必須修復。

## Proposed Solution

- R2: 在 `src/main.py` lifespan 啟動時呼叫 `check_secret_safety()`，生產環境若為預設密鑰則 raise RuntimeError
- R3: auth cookie 和 session cookie 加入 `secure=True`（可依環境判斷）
- R4: 整合 slowapi，對 login、password change、setup 端點加入速率限制
- R5: 對 form-based POST 端點加入 CSRF 防護（starlette-csrf 或 double-submit cookie）
- R6: docker-compose.yml 加入 MongoDB/Redis 認證、移除或保護 mongo-express

## Impact

- 受影響的 Spec：`user-auth`、`setup-wizard`
- 受影響的程式碼：
  - `src/main.py`（JWT check, rate limit middleware, CSRF middleware）
  - `src/core/auth/jwt.py`（check_secret_safety 強化）
  - `src/core/auth/router.py`（cookie secure flag, rate limit）
  - `src/pages/router.py`（cookie secure flag）
  - `src/shared/sessions.py`（session cookie secure flag）
  - `docker-compose.yml`（MongoDB/Redis 認證）
  - `pyproject.toml`（新增 slowapi 依賴）
