## Why

專案已累積 DSL 觸發規則系統、徽章管理 v2、安全強化、Docker 跨平台支援等重大功能，正式邁向 v1.0.0。然而 README 不符合 OSS 慣例、教師文件 API Reference 已過時、架構文件版本停在 v0.3.0、三個 crate/package 版本號分散且未同步，需要一次性整理以支撐正式版發布。

## What Changes

### 設定與 Metadata
- `pyproject.toml` — `version` 從 `0.5.0` 升至 `1.0.0`
- `crates/dsl-engine/Cargo.toml` — `version` 從 `0.1.0` 升至 `1.0.0`（隨主版本對齊）
- `crates/dsl-engine/pyproject.toml` — `version` 從 `0.1.0` 升至 `1.0.0`
- `openspec/config.yaml` — 填入 project context（tech stack、語言慣例）

### 文件
- `README.md` — 全面改版為 OSS 標準：banner.png、CI/license/version badge strip、feature overview、Quick Start（Docker Compose）、docs 索引；移除過多環境變數細節（改以連結指向 `docs/configuration.md`）
- `CHANGELOG.md` — 新增 v1.0.0 正式版條目，彙整本輪所有 features / fixes / security
- `docs/user-guide/teacher-workflow.md` — 移除過時的 API Reference 章節；新增「DSL 觸發規則管理」操作章節（CodeMirror 編輯器、Dry-run、Milkdown 說明編輯器）；更新「徽章管理」章節（Detail Modal、Soft Delete Revoke、sidebar 導覽）
- `docs/architecture.md` — 版本標頭升為 v1.0.0；架構圖加入 DSL Engine（Rust/WASM/PyO3）與 Triggers 模組
- `docs/user-guide/student-workflow.md` — 更新第 8 節，說明 `/pages/students/me/badges` 為獨立頁面（非僅 Dashboard strip）
- `docs/getting-started.md` — 加入 Docker Buildx 多架構建置說明；版本參考更新為 1.0.0

## Non-Goals

- 不修改任何 Python / Rust 應用程式碼
- 不新增測試
- 不建立新的文件頁面（所有變更均為現有檔案的更新，CHANGELOG.md 新增條目除外）
- `docs/extensions.md`、`docs/migrations.md`、`docs/security-notes.md`、`docs/configuration.md` 本次不修改（內容仍準確）

## Capabilities

### New Capabilities

（無——本次為 Refactor/Documentation，不新增功能能力）

### Modified Capabilities

- `docs-update`: 本次正式填充 docs-update spec 的 Purpose 與 Requirements，並將 v1.0.0 文件更新的範疇納入規格

## Impact

- 受影響檔案：`pyproject.toml`、`crates/dsl-engine/Cargo.toml`、`crates/dsl-engine/pyproject.toml`、`openspec/config.yaml`、`README.md`、`CHANGELOG.md`、`docs/user-guide/teacher-workflow.md`、`docs/architecture.md`、`docs/user-guide/student-workflow.md`、`docs/getting-started.md`
- 無 API 變更、無資料庫 Schema 變更、無 breaking change
