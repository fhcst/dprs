## 1. Dockerfile WASM 自建建置

- [x] 1.1 修改 Dockerfile Stage 1（`dsl-builder`）：安裝 `wasm-pack` 與 `wasm32-unknown-unknown` target，在 PyO3 wheel 建置完成後執行 `wasm-pack build --target web --out-dir /wasm-pkg --release`（涵蓋 Requirement: WASM bundle built in Docker multi-stage build）
- [x] 1.2 修改 Dockerfile Stage 2：將 `COPY ./crates/dsl-engine/pkg` 改為 `COPY --from=dsl-builder /wasm-pkg ./crates/dsl-engine/pkg`，更新註解移除「pre-built, checked into repo」描述（涵蓋 Requirement: Dual compilation targets — Docker build does not depend on local WASM artifacts；Requirement: Cross-platform build and push — No pre-built artifacts required）

## 2. 建置產物 gitignore 清理

- [x] [P] 2.1 在 `.gitignore` 中新增 `src/static/css/tailwind.css` 條目，標記為 Tailwind 建置產物（涵蓋 Requirement: Tailwind CSS output classified as build artifact）
- [x] [P] 2.2 刪除 `scripts/migrations/role_to_permissions.py`，確保 migrations 目錄只包含符合 `YYYYMMDD_NNN_*.py` 命名規範的檔案（涵蓋 Requirement: Migration directory contains only conforming files）

## 3. 驗證

- [x] 3.1 執行 `uv run python -m pytest` 確認所有現有測試通過（確保刪除 migration 檔案與 gitignore 變更不影響既有功能）
- [x] 3.2 執行 `docker build .` 驗證完整 Docker image 建置成功，確認 image 內 `/app/crates/dsl-engine/pkg/` 包含有效的 `dsl_engine.js` 與 `dsl_engine_bg.wasm`
