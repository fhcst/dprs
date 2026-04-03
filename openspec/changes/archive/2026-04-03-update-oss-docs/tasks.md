## 1. README.md 更新

- [x] 1.1 技術堆疊區新增 Rust（pest PEG parser）、WebAssembly（wasm-pack）、PyO3（maturin）至技術清單
- [x] 1.2 功能特色的遊戲化區塊新增 DSL 觸發規則系統說明（教師可用表達式語言定義觸發條件、CodeMirror 6 編輯器、前端 dry-run 測試）— 對應 Requirement「Project documentation reflects DSL engine and trigger-rule system」
- [x] 1.3 快速開始區新增 Rust toolchain 為選用依賴的說明（不安裝 Rust 仍可正常執行，觸發規則功能會顯示明確錯誤）

## 2. CHANGELOG.md 更新

- [x] 2.1 新增 v0.6.0 版本區塊，包含：Added（DSL 引擎 crate、觸發規則管理 CRUD + 頁面、CodeMirror 6 + WASM 即時驗證、Milkdown WYSIWYG 徽章說明編輯器、DSL Help Modal、stats API、GitHub Actions CI）、Changed（Dockerfile 改為 multi-stage build、`get_all()` 回傳 dict + deps.py 轉 list、`review_join_request()` 新增 class_id 驗證）、Fixed（P0 `get_reward_providers()` dict 迭代崩潰、join-request 跨班授權漏洞、ClassMembership 重複建立、Discord override 欄位未傳遞）、Security（ClassMembership unique compound index、DSL 沙箱白名單制、`ensure_membership()` atomic upsert）

## 3. CONTRIBUTING.md 更新

- [x] [P] 3.1 開發環境設定新增 Rust toolchain 安裝步驟：`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`、`rustup target add wasm32-unknown-unknown`、`cargo install wasm-pack`
- [x] [P] 3.2 專案結構區新增 `crates/dsl-engine/` 說明（src/ 各模組用途、dsl.pest grammar、WASM/PyO3 binding modules）
- [x] 3.3 新增「Rust DSL Engine 開發」區塊：WASM build（`wasm-pack build --target web --out-dir pkg`）、PyO3 build（`maturin develop --features python`）、測試（`cargo test --lib`）、justfile 使用說明

## 4. SECURITY.md 更新

- [x] [P] 4.1 新增「DSL 沙箱安全模型」區塊：純求值無 I/O、白名單制變數與函數、無賦值/迴圈、class-scoped 資料隔離（CBAC）、service 層注入預計算 context
- [x] [P] 4.2 新增「ClassMembership 唯一性保障」區塊：unique compound index、atomic upsert、DuplicateKeyError 處理
- [x] [P] 4.3 新增「Rich Text Editor 安全」區塊：Milkdown 使用 ProseMirror（sanitized DOM）、CodeMirror 6 不執行使用者輸入、WASM 在瀏覽器沙箱中執行

## 5. docs/architecture.md 更新

- [x] 5.1 系統概覽區新增 DSL 引擎架構圖（Rust crate → WASM 前端 / PyO3 後端、CodeMirror 6 接線、觸發評估流程）
- [x] 5.2 模組結構區新增 `crates/dsl-engine/` 和 `src/gamification/triggers/` 模組說明
- [x] 5.3 資料模型區新增 `TriggerRule` document 和 `BadgeDefinition.trigger_rule_id` 欄位、ClassMembership unique index 說明
- [x] 5.4 技術堆疊表新增 Rust（pest, wasm-bindgen, pyo3）、前端新增 CodeMirror 6 + Milkdown

## 6. docs/extensions.md 更新

- [x] 6.1 新增「DSL 觸發規則與 Code Trigger 共存」區塊：說明 `trigger_key`（ExtensionRegistry 程式碼觸發器）和 `trigger_rule_id`（DSL 規則）的互斥模型、`evaluate_triggers_for_event()` 合併評估流程
- [x] 6.2 新增 `ensure_membership()` public API 說明（atomic upsert、適用場景）

## 7. docs/getting-started.md 更新

- [x] [P] 7.1 前置需求區新增 Rust toolchain 為選用項目（僅在修改 DSL 引擎程式碼時需要），列出安裝指令
- [x] [P] 7.2 本機開發區新增「DSL 引擎建置（選用）」步驟：`cd crates/dsl-engine && maturin develop --features python`，說明不建置時的 graceful fallback 行為
