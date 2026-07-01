## 1. JWT 密鑰啟動檢查

- [x] 1.1 在 `src/main.py` lifespan 啟動時呼叫 `check_secret_safety()`，生產環境若為預設密鑰 raise RuntimeError（JWT secret validation at startup）

## 2. Cookie Secure 旗標

- [x] [P] 2.1 在 `src/core/auth/router.py` 和 `src/pages/router.py` 的 set_cookie 呼叫加入 `secure=True`（依環境判斷）（auth cookies use Secure flag in production）
- [x] [P] 2.2 在 `src/shared/sessions.py` 的 security_flags 加入 `; secure`（依環境判斷）

## 3. 速率限制

- [x] 3.1 在 `pyproject.toml` 新增 slowapi 依賴，在 `src/main.py` 加入 SlowAPI middleware
- [x] 3.2 對 `POST /auth/login`、`POST /pages/login`、`POST /auth/change-password`、`POST /setup` 加入速率限制 decorator

## 4. CSRF 防護

- [x] 4.1 對 form-based POST 端點加入 Origin/Referer 檢查 middleware 或 double-submit cookie pattern

## 5. Docker 基礎設施安全

- [x] [P] 5.1 在 `docker-compose.yml` 加入 MongoDB 認證（MONGO_INITDB_ROOT_USERNAME/PASSWORD），更新 app 的 MONGO_URL
- [x] [P] 5.2 在 `docker-compose.yml` 加入 Redis 認證（--requirepass），bind ports to 127.0.0.1，移除或保護 mongo-express
