# DPRS 組態設定指南

本文件說明「每日訓練繳交系統」(Daily Practice Record System, DPRS) 的所有環境變數與 Docker 服務設定。

---

## 1. 環境變數總覽

所有環境變數皆透過 `.env` 檔案提供給 `docker-compose.yml`。建立專案時，請先複製範本：

```bash
cp .env.example .env
```

再依需求修改各項數值。

### 完整變數表

| 變數名稱 | 說明 | 預設值 | 必填（生產環境） |
|---|---|---|---|
| `FASTAPI_APP_ENVIRONMENT` | 應用程式執行環境。`dev` 為開發模式，`production` 為正式模式 | `dev` | 是 |
| `SESSION_SECRET` | JWT (JSON Web Token，JSON 網路權杖) 簽署密鑰，用於 Session Cookie 與 Access Token 的加密簽章 | `dev-secret-change-in-production` | **是** |
| `MONGO_URL` | MongoDB 連線字串 (Connection String)，由 `docker-compose.yml` 自動組裝，格式為 `mongodb://<username>:<password>@mongo:27017` | — (自動產生) | — |
| `MONGO_DB_NAME` | MongoDB 資料庫名稱 | `dts2` | 否 |
| `MONGO_ROOT_USERNAME` | MongoDB 管理員帳號，用於資料庫驗證 (Authentication) | `admin` | 否 |
| `MONGO_ROOT_PASSWORD` | MongoDB 管理員密碼 | 無預設值 | **是** |
| `REDIS_URL` | Redis 連線字串，由 `docker-compose.yml` 自動組裝，格式為 `redis://:<password>@redis:6379/0` | — (自動產生) | — |
| `REDIS_PASSWORD` | Redis 認證密碼，透過 `--requirepass` 參數啟用 | 無預設值 | **是** |
| `ME_USER` | Mongo Express 網頁管理介面的 Basic Auth (基本驗證) 帳號 | `admin` | 否 |
| `ME_PASSWORD` | Mongo Express 網頁管理介面的 Basic Auth 密碼 | 無預設值 | 僅 debug 時需要 |
| `JWT_EXPIRES_SECONDS` | JWT Access Token 有效期限，單位為秒 | `86400` (24 小時) | 否 |
| `FORWARDED_ALLOW_IPS` | 受信任的反向代理 (Reverse Proxy) IP 位址清單，對應 Uvicorn 的 `--forwarded-allow-ips` 參數 | `""` (空字串，不信任任何代理) | 視部署架構而定 |

### 變數使用位置

- **`SESSION_SECRET`** — 同時用於兩處：
  1. `SessionMiddleware`：Session Cookie 的 JWT 簽署 (`src/main.py`)
  2. JWT Access Token：登入後發行的權杖簽署 (`src/core/auth/jwt.py`)

- **`MONGO_URL`** 與 **`REDIS_URL`** — 在 `docker-compose.yml` 中以 `MONGO_ROOT_USERNAME`、`MONGO_ROOT_PASSWORD`、`REDIS_PASSWORD` 等變數自動組裝，應用程式端直接讀取組裝後的完整連線字串。

- **`JWT_EXPIRES_SECONDS`** — 僅影響 Access Token（存放於 `access_token` Cookie）的有效期限。Session Cookie 另有獨立的 `max_age` 設定（預設同為 24 小時）。

---

## 2. Docker 服務設定

系統由四個 Docker 服務組成，定義於 `docker-compose.yml`。

### 2.1 app — FastAPI 應用程式

| 項目 | 內容 |
|---|---|
| 建置方式 | 使用專案根目錄的 `Dockerfile` 建置 |
| 基底映像檔 | `python:3.13-slim-trixie` |
| 套件管理 | 使用 [uv](https://docs.astral.sh/uv/) 安裝相依套件 |
| 對外連接埠 | `8000:8000` |
| 重啟策略 | `unless-stopped` |
| 掛載磁碟區 | `./src:/app/src`（開發時即時同步程式碼） |
| 啟動依賴 | 等待 `mongo` 與 `redis` 通過 Health Check (健康檢查) 後才啟動 |

**啟動流程**（`scripts/docker-entrypoint.sh`）：

- 當 `FASTAPI_APP_ENVIRONMENT=prod` 時，以 `fastapi run`（正式模式）啟動
- 其餘情況以 `fastapi dev`（開發模式，含自動重載）啟動

**傳入的環境變數**：

```yaml
environment:
  - FASTAPI_APP_ENVIRONMENT=${FASTAPI_APP_ENVIRONMENT:-dev}
  - SESSION_SECRET=${SESSION_SECRET}
  - MONGO_URL=mongodb://${MONGO_ROOT_USERNAME:-admin}:${MONGO_ROOT_PASSWORD}@mongo:27017
  - MONGO_DB_NAME=${MONGO_DB_NAME:-dts2}
  - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

### 2.2 mongo — MongoDB 8.0

| 項目 | 內容 |
|---|---|
| 映像檔 | `mongo:8.0` |
| 驗證模式 | 已啟用驗證 (Authentication)，使用 `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD` 建立管理員帳號 |
| 連接埠 | `127.0.0.1:27017:27017` — 僅綁定 Loopback (迴路位址)，外部網路無法直接存取 |
| 資料持久化 | 使用具名磁碟區 (Named Volume) `mongo_data` 掛載至 `/data/db` |
| 健康檢查 | 每 10 秒執行 `mongosh` 連線 `ping` 指令，逾時 5 秒，最多重試 5 次 |
| 重啟策略 | `unless-stopped` |

### 2.3 redis — Redis 7

| 項目 | 內容 |
|---|---|
| 映像檔 | `redis:7-alpine` |
| 驗證模式 | 以 `--requirepass` 啟用密碼驗證 |
| 連接埠 | `127.0.0.1:6379:6379` — 僅綁定 Loopback，外部網路無法直接存取 |
| 健康檢查 | 每 10 秒執行 `redis-cli ping`，逾時 5 秒，最多重試 5 次 |
| 重啟策略 | `unless-stopped` |

### 2.4 mongo-express — MongoDB 網頁管理介面

| 項目 | 內容 |
|---|---|
| 映像檔 | `mongo-express:1.0` |
| Compose Profile | `debug` — **預設不啟動**，需以 `--profile debug` 明確啟用 |
| 連接埠 | `8081:8081` |
| 驗證方式 | Basic Auth，帳號密碼由 `ME_USER` / `ME_PASSWORD` 控制 |
| 啟動依賴 | 等待 `mongo` 通過健康檢查 |
| 重啟策略 | `unless-stopped` |

**啟用方式**：

```bash
docker compose --profile debug up -d
```

> **注意**：Mongo Express 僅供開發偵錯使用，切勿在正式環境中啟用。

---

## 3. 生產環境注意事項

### 3.1 SESSION_SECRET — 必須設定安全密鑰

`SESSION_SECRET` 在未設定時會使用預設值 `dev-secret-change-in-production`。當 `FASTAPI_APP_ENVIRONMENT=production` 時，系統會在啟動階段呼叫 `check_secret_safety()` 直接拋出 `RuntimeError`，**拒絕啟動**。

產生安全密鑰的建議方式：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 資料庫密碼 — 必須設定

- `MONGO_ROOT_PASSWORD` — MongoDB 管理員密碼，未設定將導致連線字串不完整
- `REDIS_PASSWORD` — Redis 認證密碼，未設定將導致 `--requirepass` 收到空值

兩者皆無預設值，務必在 `.env` 中明確設定強密碼。

### 3.3 Cookie Secure 旗標

當 `FASTAPI_APP_ENVIRONMENT=production` 時：

- **Access Token Cookie**（`access_token`）：登入端點 `/auth/login` 會將 `secure=True` 寫入 Cookie 屬性，瀏覽器僅在 HTTPS 連線下傳送此 Cookie
- **Session Cookie**（`session`）：`SessionMiddleware` 會在回應標頭附加 `; secure` 旗標

確保正式環境已啟用 HTTPS (TLS)，否則瀏覽器將不會傳送這些 Cookie，導致驗證失敗。

### 3.4 速率限制 (Rate Limiting)

系統使用 [SlowAPI](https://github.com/laurentS/slowapi) 對敏感端點實施速率限制，以 Client IP 作為識別鍵：

| 端點 | 限制 |
|---|---|
| `POST /auth/login` | 每分鐘 10 次 |
| `POST /auth/change-password` | 每分鐘 5 次 |

超過限制時回傳 HTTP 429 Too Many Requests。

### 3.5 CSRF 防護

`CSRFMiddleware` 對所有表單 POST 請求（Content-Type 為 `application/x-www-form-urlencoded` 或 `multipart/form-data`）進行 Origin/Referer 標頭驗證：

- 若 `Origin` 標頭存在且與 `Host` 不一致，回傳 HTTP 403
- 若 `Origin` 不存在但 `Referer` 存在且與 `Host` 不一致，回傳 HTTP 403
- 若兩者皆不存在（例如直接 API 呼叫、同站導覽），則放行——此情境由 Cookie 的 `SameSite=Lax` 屬性提供防護

JSON API 呼叫不受此中介軟體影響。

### 3.6 反向代理設定 — FORWARDED_ALLOW_IPS

若系統部署於反向代理（如 Nginx、Caddy、Traefik）後方，必須設定 `FORWARDED_ALLOW_IPS` 以確保 Uvicorn 正確解析用戶端 IP。此變數直接對應 Uvicorn 的 `--forwarded-allow-ips` 參數。

```bash
# 信任來自 127.0.0.1 的代理標頭
FORWARDED_ALLOW_IPS=127.0.0.1

# 信任所有代理（僅在受控網路中使用）
FORWARDED_ALLOW_IPS=*
```

未正確設定此值將導致：

- 速率限制以代理伺服器 IP 計算，而非實際用戶端 IP
- 記錄檔 (Log) 中的來源 IP 不正確

### 3.7 生產環境 `.env` 範例

```dotenv
FASTAPI_APP_ENVIRONMENT=production
SESSION_SECRET=<由 secrets.token_hex(32) 產生的隨機字串>

MONGO_DB_NAME=dts2
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=<強密碼>

REDIS_PASSWORD=<強密碼>

JWT_EXPIRES_SECONDS=86400

FORWARDED_ALLOW_IPS=127.0.0.1
```
