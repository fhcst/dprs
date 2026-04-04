## 1. Dockerfile 與 entrypoint 修正

- [x] 1.1 [P] 修改 `Dockerfile`：加入 `COPY ./scripts ./scripts`，將完整 `scripts/` 目錄複製進 image；移除原本單獨 COPY `docker-entrypoint.sh` 到根目錄的指令，改用 `./scripts/docker-entrypoint.sh` 作為 ENTRYPOINT（對應 Requirement: Scripts directory included in Docker image）
- [x] 1.2 [P] 修改 `scripts/docker-entrypoint.sh`：在啟動 FastAPI server 前，依序執行 `uv run python scripts/migrate.py init` 與 `uv run python scripts/migrate.py up`，確保 automatic migration on container startup；shell 腳本須維持 `set -e` 使 migration 失敗時 container 立即停止

## 2. Migration CLI 模組載入修正

- [x] 2.1 修改 `scripts/migrate.py`：在既有的 `sys.path.insert` 前加入一行，將專案根目錄（`Path(__file__).parent.parent`）加入 `sys.path`，確保 Migration module importable in container environment，使 `importlib.import_module("scripts.migrations.*")` 在所有執行環境中正確運作（對應 Requirement: Migration CLI 中 sys.path 的新增要求）

## 3. Beanie model index 定義與 migration 一致性修正

- [x] 3.1 修改 `src/core/users/models.py`：將 `Settings.indexes` 中的 `"username"` 從普通 index 改為 `IndexModel([("username", 1)], unique=True)`，與 migration `20260317_001_initial_indexes.py` 的定義一致，避免 `IndexKeySpecsConflict` 錯誤

## 4. 環境變數文件補齊

- [x] 4.1 更新 `.env.example`：補齊 `JWT_EXPIRES_SECONDS`、`UVICORN_HOST`、`UVICORN_PORT`、`FORWARDED_ALLOW_IPS` 等缺漏變數；加入繁體中文註解說明每個變數的用途與預設值，標記 `[必填]` / `[選填]`
