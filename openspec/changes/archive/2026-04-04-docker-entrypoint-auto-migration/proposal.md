## Why

目前 Docker container 啟動時，`docker-entrypoint.sh` 直接啟動 FastAPI server，未先執行 database migration。這導致：

1. 部署新版本時需要手動執行 `migrate.py init` 與 `migrate.py up`，容易遺漏
2. 應用程式可能在 schema 尚未更新的狀態下啟動，造成執行期錯誤
3. Beanie model �� index 定義與 migration 建立的 index 不一致（例如 `username` index 的 unique 屬性衝突），導致 `init_beanie` 時 `IndexKeySpecsConflict` 錯誤

## What Changes

- `scripts/docker-entrypoint.sh`：啟動 FastAPI server 前，自動執行 `migrate.py init` 與 `migrate.py up`，確保所有 pending migrations 已套用
- `Dockerfile`：加入 `COPY ./scripts ./scripts`，將完整的 `scripts/` 目錄（含 `migrate.py` 與 `migrations/`）複製進 image；統一 entrypoint 路徑為 `./scripts/docker-entrypoint.sh`
- `scripts/migrate.py`：將專案根目錄加入 `sys.path`，修正 container 內 `importlib.import_module("scripts.migrations.*")` 的 `ModuleNotFoundError`
- `src/core/users/models.py`：將 `username` index 從普通 index 改為 `unique=True`，與 migration `20260317_001_initial_indexes.py` 的定義一致
- `.env.example`：補齊 `JWT_EXPIRES_SECONDS`、`UVICORN_HOST`、`UVICORN_PORT`、`FORWARDED_ALLOW_IPS` 等缺漏變數，加入繁體中文註解說明

## Non-Goals

- 不改變 migration 機制本身（`migrate.py` 的 init/up/down/status 指令邏輯不變）
- 不引入 migration 版本鎖或並行執行保護（目前為單一 container 部署）
- 不處理 migration 失敗後的自動回滾（`set -e` 確保失敗時 container 停止，由 orchestrator 處理重啟策略）

## Capabilities

### New Capabilities

（無新增 capability — 本次變更是對既有基礎設施的修正與強化）

### Modified Capabilities

- `migration-scripts`：新增「container 啟動時自動執行 migration」的需求，並修正 migration 模組在 container 環境中的載入路徑問題

## Impact

- 受影響的 specs：`migration-scripts`
- 受影響的程式碼：
  - `scripts/docker-entrypoint.sh`（新增 migration 執行步驟）
  - `Dockerfile`（新增 COPY scripts、調整 ENTRYPOINT 路徑）
  - `scripts/migrate.py`（sys.path 修正）
  - `src/core/users/models.py`（index 定義修正）
  - `.env.example`（補齊變數與註解）
