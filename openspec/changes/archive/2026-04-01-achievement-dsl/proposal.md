## Why

目前成就觸發條件（BadgeTrigger）只能由開發者以 Python Protocol 實作並註冊到 ExtensionRegistry。教師若需新增觸發邏輯（例如「連續打卡 7 天且繳交次數 ≥ 3」），必須請開發者撰寫程式碼。這導致教師無法自主管理成就規則，新增成就的回饋週期過長。

本變更引入 DSL（Domain-Specific Language）表達式系統，讓教師在 Web UI 上直接撰寫觸發規則。DSL 引擎以 Rust 實作，編譯為 WASM（前端即時驗證、autocomplete、dry-run 測試）與 PyO3 native binding（後端驗證與執行），確保前後端行為一致。現有開發者 Python Protocol 機制完整保留。

## What Changes

- 新增 Rust crate `dsl-engine`，提供 DSL 解析、驗證、求值、自動補全、hover 提示、規則描述生成、help 內容輸出功能，編譯為 WASM 與 PyO3 雙目標
- 新增 `TriggerRule` MongoDB collection，儲存教師撰寫的 DSL 觸發規則（class-scoped）
- `BadgeDefinition` model 新增 `trigger_rule_id` 欄位，與 `trigger_key` 互斥，支援綁定 DSL 規則
- 觸發評估流程（`evaluate_triggers_for_event`）合併兩種觸發來源：ExtensionRegistry 程式碼觸發器 + DSL 規則引擎
- 新增「觸發規則管理」頁面：CodeMirror 6 編輯器 + WASM 即時驗證/autocomplete/hover
- 新增「規則測試」功能：前端 WASM dry-run，透過 stats API 取得班級學生聚合資料，顯示符合/不符合的學生清單
- 徽章管理頁面的「說明」欄位升級為 Milkdown WYSIWYG Markdown 編輯器，採用 G2 分區塊模式（自動產生條件摘要 + 教師自由撰寫區）
- 新增 DSL Help Modal（`[?]` 按鈕），內容由 Rust crate 定義生成，支援 locale

## Non-Goals

- 不取代現有 Python Protocol BadgeTrigger 機制 — 開發者程式碼注入完整保留
- DSL 不提供資料寫入能力 — 純求值，回傳 bool
- DSL 不提供跨 class 資料存取 — 嚴格遵守 CBAC class-scoped 隔離
- DSL 不提供任意函數呼叫 — 僅白名單制內建函數
- 不建立獨立的 LSP server — 透過 WASM export + CodeMirror extensions 實現 LSP-like 體驗
- 不支援 DSL 規則的版本管理或 diff — 未來可擴展但不在本次範圍

## Capabilities

### New Capabilities

- `dsl-engine`: Rust DSL 表達式引擎 — 解析、驗證、求值、自動補全、hover 提示、describe、help 內容生成，雙編譯目標（WASM + PyO3）
- `trigger-rule-management`: 觸發規則 CRUD 管理 — TriggerRule model、API endpoints、教師管理頁面（CodeMirror 6 編輯器 + WASM 整合）
- `rule-dry-run`: 規則前端測試 — stats API 提供 class-scoped 學生聚合資料，WASM evaluate dry-run 顯示符合結果
- `badge-description-editor`: 徽章說明 WYSIWYG 編輯 — Milkdown Markdown 編輯器、G2 分區塊模式（自動條件摘要 + 自由撰寫區）、Rust describe() 產生條件文字
- `dsl-help-modal`: DSL 撰寫說明 Modal — 從 Rust crate 定義動態生成變數/運算子/函數/範例內容，支援 locale

### Modified Capabilities

- `badge-system`: BadgeDefinition 新增 `trigger_rule_id` 欄位；`evaluate_triggers_for_event` 合併 DSL 規則評估路徑
- `extension-registry`: BadgeTrigger Protocol 不變，但文件需更新以說明與 DSL 的共存模型

## Impact

- 新增 Rust crate：`crates/dsl-engine/`（WASM + PyO3 編譯）
- 新增前端依賴：CodeMirror 6、Milkdown、dsl-engine WASM package
- 後端依賴：dsl-engine PyO3 native binding
- 受影響程式碼：
  - `src/gamification/badges/models.py` — BadgeDefinition 新增欄位
  - `src/gamification/badges/service.py` — 合併評估流程
  - `src/gamification/badges/router.py` — 新增 stats endpoint
  - 新增 `src/gamification/triggers/` — TriggerRule model、service、router
  - 新增 `src/templates/teacher/trigger-rules.html` — 規則管理頁面
  - 修改 `src/templates/teacher/badges.html`（若存在）或新增 — 徽章管理含 Milkdown
  - `src/templates/shared/base.html` — 載入 WASM、CodeMirror、Milkdown 資源
- Build pipeline：新增 Rust toolchain、wasm-pack、maturin（PyO3 build）
- CI/CD：新增 Rust crate 測試、WASM 編譯、PyO3 wheel 建置步驟
