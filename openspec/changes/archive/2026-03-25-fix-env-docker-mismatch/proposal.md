## Why

`.env` 和 `.env.example` 仍然包含舊的 MariaDB 設定（`MARIADB_ROOT_PASSWORD`、`MARIADB_DATABASE` 等），但 `docker-compose.yml` 已改為 MongoDB + Redis 架構。這導致 `docker compose up` 時所有密碼變數為空白字串，MongoDB healthcheck 失敗，整個服務無法啟動。

## What Changes

- 更新 `.env.example`：移除 MariaDB 變數，改為 MongoDB + Redis 所需的變數（`MONGO_ROOT_PASSWORD`、`REDIS_PASSWORD`、`ME_PASSWORD` 等）
- 更新 `.env`：與 `.env.example` 同步，填入本機開發用的預設值

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

（無 — 這是基礎設施配置修復，不涉及 spec 層級的行為變更）

## Impact

- 受影響檔案：`.env`、`.env.example`
- 修復後 `docker compose up -d --build` 可正常啟動 MongoDB、Redis、App 三個容器
