## 1. 移除舊的 MariaDB 變數

- [x] [P] 1.1 從 `.env.example` 移除 `MARIADB_*`、`DB_HOST`、`DB_PORT` 等舊變數
- [x] [P] 1.2 從 `.env` 移除對應的舊變數

## 2. 新增 MongoDB + Redis 變數

- [x] [P] 2.1 在 `.env.example` 新增 `MONGO_ROOT_USERNAME`、`MONGO_ROOT_PASSWORD`、`MONGO_DB_NAME`、`REDIS_PASSWORD`、`ME_USER`、`ME_PASSWORD`、`SESSION_SECRET`、`FASTAPI_APP_ENVIRONMENT`，使用 `changeme_*` 提示值
- [x] [P] 2.2 在 `.env` 使用明確的開發用密碼填入相同變數（非空白值）

## 3. 驗證

- [x] 3.1 執行 `docker compose up -d --build` 確認無環境變數警告且所有容器正常啟動
