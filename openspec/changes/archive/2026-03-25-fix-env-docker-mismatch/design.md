## Context

`docker-compose.yml` 使用 MongoDB 8.0 + Redis 7 作為資料庫與快取，並透過環境變數注入密碼。但 `.env` 和 `.env.example` 仍保留舊的 MariaDB 設定，導致 `MONGO_ROOT_PASSWORD`、`REDIS_PASSWORD` 等變數未定義，容器啟動失敗。

## Goals / Non-Goals

**Goals:**

- 讓 `.env.example` 列出 `docker-compose.yml` 所需的所有環境變數
- 讓 `.env` 包含可直接用於本機開發的預設值
- `docker compose up -d --build` 可一次成功啟動

**Non-Goals:**

- 不修改 `docker-compose.yml` 的架構
- 不處理 production 部署的密鑰管理

## Decisions

### 移除舊的 MariaDB 變數

`.env` 和 `.env.example` 中的 `MARIADB_*`、`DB_HOST`、`DB_PORT` 已無對應服務，全部移除。

### 新增 MongoDB + Redis 變數

依據 `docker-compose.yml` 的引用，需要以下變數：

| 變數 | 用途 | `.env.example` 預設值 |
|---|---|---|
| `MONGO_ROOT_USERNAME` | MongoDB root 使用者名稱 | `admin` |
| `MONGO_ROOT_PASSWORD` | MongoDB root 密碼 | `changeme_mongo` |
| `MONGO_DB_NAME` | 預設資料庫名稱 | `dts2` |
| `REDIS_PASSWORD` | Redis 認證密碼 | `changeme_redis` |
| `ME_USER` | Mongo Express Basic Auth 帳號 | `admin` |
| `ME_PASSWORD` | Mongo Express Basic Auth 密碼 | `changeme_me` |
| `SESSION_SECRET` | FastAPI session 密鑰 | `changeme_session` |
| `FASTAPI_APP_ENVIRONMENT` | 應用環境 | `dev` |

### `.env` 使用明確的開發用密碼

`.env` 填入簡單但非空白的密碼（如 `devpassword`），確保本機開發可直接啟動。`.env.example` 使用 `changeme_*` 提示使用者需替換。

## Risks / Trade-offs

- **[風險] `.env` 包含明文密碼** → `.env` 已在 `.gitignore` 中，且僅用於本機開發。Production 應使用環境變數注入或 secrets manager。
- **[風險] 開發者已有自訂 `.env`** → 這是修復，開發者需自行更新。`.env.example` 提供完整參考。
