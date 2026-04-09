## Why

目前 Dockerfile 第 50-51 行透過 `COPY ./crates/dsl-engine/pkg` 複製 WASM bundle，但 `pkg/` 內的所有建置產物都被 `pkg/.gitignore`（內容為 `*`）排除於版本控制之外。這意味著 fresh clone 後直接 `docker build` 會得到一個缺少前端 DSL 驗證功能的 image。此外，CI workflow 雖然會建置 WASM 並上傳為 GitHub artifact，但並未將產物回寫至 Docker build context。

附帶問題：`src/static/css/tailwind.css`（本地建置產物）目前未被 git 追蹤也未被 gitignore，處於曖昧狀態；`scripts/migrations/role_to_permissions.py` 不符合 migration 命名規範，不會被自動執行。

## What Changes

- Dockerfile Stage 1（`dsl-builder`）新增 wasm-pack 安裝與 WASM bundle 建置，使 PyO3 wheel 與 WASM bundle 在同一 stage 產出
- Stage 2 改為 `COPY --from=dsl-builder` 取用 WASM bundle，移除對本地 `pkg/` 預建產物的依賴
- `src/static/css/tailwind.css` 加入 `.gitignore`，明確標記為建置產物
- 清理 `scripts/migrations/` 中不符合命名規範的遺留檔案 `role_to_permissions.py`

## Non-Goals

- 不改動 CI workflow（`dsl-engine.yml`）—— CI 的 wasm-build job 仍作為獨立驗證用途
- 不新增 pytest 或 Docker build 的 CI workflow（後續再處理）
- 不更改 WASM 前端載入邏輯或 graceful degradation 行為

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `docker-buildx`: Dockerfile multi-stage 建置流程變更 — Stage 1 同時產出 PyO3 wheel 與 WASM bundle
- `dsl-engine`: WASM bundle 的產出路徑從本地預建改為 Docker 內建置
- `tailwind-build`: `tailwind.css` 明確歸類為建置產物並加入 gitignore
- `migration-scripts`: 清理不符合命名規範的遺留 migration 檔案

## Impact

- 受影響檔案：`Dockerfile`、`.gitignore`、`scripts/migrations/role_to_permissions.py`
- Docker image 建置時間增加約 30-60 秒（wasm-pack build）
- 建置後 image 功能與現有完全一致，無 API 或行為變更
- 消除「fresh clone 後 Docker build 缺少 WASM」的隱性建置斷裂
