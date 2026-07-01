## 1. Rust DSL Engine Crate 建置

- [x] [P] 1.1 在 `crates/dsl-engine/` 建立 Rust crate，設定 Cargo.toml 含 `pest`、`wasm-bindgen`、`pyo3` 依賴，建立 WASM（wasm-pack）與 PyO3（maturin）雙編譯目標結構 — Decision: Rust 單一 crate 雙編譯目標（R1 架構）；Requirement「Dual compilation targets」
- [x] 1.2 使用 pest PEG parser generator 實作 DSL grammar，支援比較運算子（`==`, `!=`, `>`, `>=`, `<`, `<=`）、邏輯運算子（`AND`, `OR`, `NOT`）、括號分組、數字/字串/布林字面值、dot-notation 變數存取 — Decision: DSL 語法設計 — S2 表達式語言；Requirement「DSL expression parsing」
- [x] 1.3 實作 `validate()` 函數，對 AST 進行語意驗證：檢查變數名稱是否在白名單（`checkin_count`, `checkin_streak`, `submission_count`, `points`, `badge_count`, `event.type`, `event.occurred_at`）、函數名稱是否在白名單（`count`, `day_of_week`）、型別相容性檢查 — 對應 Requirement「DSL expression validation」
- [x] 1.4 實作 `evaluate()` 函數，接收 `EvalContext` struct 對表達式求值，回傳 `Result<bool, EvalError>`，不做任何 I/O — Decision: DSL 安全沙箱與 CBAC 整合；Requirement「DSL expression evaluation」
- [x] 1.5 實作 `complete()` 函數，根據 source 與 cursor position 回傳上下文相關的自動補全建議（變數名、運算子、函數參數）— 對應 Requirement「DSL autocomplete suggestions」
- [x] 1.6 實作 `hover_info()` 函數，根據 cursor position 回傳 token 的型別與 locale 化描述 — 對應 Requirement「DSL hover information」
- [x] 1.7 實作 `describe()` 函數，將 AST 轉換為 locale 化的 Markdown 條件摘要，AND 條件產生 bullet list，OR 條件用「或」分隔 — 對應 Requirement「DSL expression describe」
- [x] 1.8 實作 `get_help_content()` 函數，回傳含 variables、operators、functions、examples 的結構化 JSON，搭配 `locale/tw.json` 繁中翻譯檔 — Decision: DSL Help Modal；Requirement「DSL help content generation」
- [x] 1.9 撰寫 Rust 單元測試，涵蓋 parse/validate/evaluate/complete/hover_info/describe/get_help_content 各函數的正常與邊界情境
- [x] 1.10 設定 wasm-pack build 產出 npm package，確認 WASM export 包含所有 7 個 public API；設定 maturin build 產出 Python wheel，確認 `import dsl_engine` 可用 — 對應 Requirement「Dual compilation targets」中 WASM 與 PyO3 可匯入的場景

## 2. 後端 TriggerRule Model 與 Service

- [x] [P] 2.1 在 `src/gamification/triggers/models.py` 建立 `TriggerRule` Beanie Document（`class_id`, `name`, `expression`, `is_active`, `created_by`, `created_at`, `updated_at`），collection 名 `triggerrules` — Decision: 觸發規則與徽章分離管理（F2 架構）；Requirement「TriggerRule data model」
- [x] 2.2 在 `src/gamification/triggers/service.py` 實作 TriggerRule CRUD service 函數，create/update 時呼叫 PyO3 `dsl_engine.validate()` 驗證表達式，delete 時檢查是否有 BadgeDefinition 綁定 — 對應 Requirement「TriggerRule CRUD API endpoints」中建立/刪除的場景
- [x] [P] 2.3 在 `src/gamification/badges/models.py` 的 BadgeDefinition 新增 `trigger_rule_id: Optional[str]` 欄位，加入 `trigger_key` 與 `trigger_rule_id` 互斥驗證 — 對應 Requirement「BadgeDefinition binding to trigger rule」及 Requirement「Badge definition by teacher」中 Mutual exclusion 的場景

## 3. 後端 API Endpoints

- [x] 3.1 在 `src/gamification/triggers/router.py` 實作 TriggerRule CRUD 五個 REST endpoints（POST/GET list/GET single/PUT/DELETE），所有端點加上 `require_permission(MANAGE_OWN_CLASS)` + `can_manage_class()` CBAC 驗證 — 對應 Requirement「TriggerRule CRUD API endpoints」
- [x] 3.2 在 `src/gamification/badges/router.py` 新增 `GET /api/classes/{class_id}/students/stats` endpoint，回傳班級學生聚合統計值，支援 `windows` query parameter 的時間窗口預計算 — 對應 Requirement「Student stats aggregation API」
- [x] 3.3 修改 `src/gamification/badges/router.py` 的 badge CRUD endpoints，支援 `trigger_rule_id` 欄位，確保 `trigger_key`/`trigger_rule_id` 互斥驗證 — 對應 Requirement「Badge definition by teacher」中 Mutual exclusion enforced 的場景

## 4. 後端觸發評估流程合併

- [x] 4.1 修改 `src/gamification/badges/service.py` 的 `evaluate_triggers_for_event()` 函數，在現有 code trigger 評估路徑之後，新增 DSL rule 評估路徑：載入 TriggerRule → 建構 EvalContext → 呼叫 `dsl_engine.evaluate()` → 符合條件時 `award_badge()`。跳過 `is_active: false` 的規則 — Decision: 觸發規則與徽章分離管理（F2 架構）；Requirement「DSL trigger evaluation in badge award flow」及 Requirement「Protocol definitions for extension points」共存模型
- [x] 4.2 實作 `build_eval_context()` helper 函數，從 MongoDB 查詢該 class_id 內該學生的聚合統計值，填入 EvalContext 所有欄位（checkin_count, checkin_streak, submission_count, points, badge_count, event.*）— Decision: DSL 安全沙箱與 CBAC 整合

## 5. 前端 — 觸發規則管理頁面

- [x] [P] 5.1 建立 `src/templates/teacher/trigger-rules.html` 頁面，顯示規則列表（名稱、表達式預覽、啟用狀態、綁定徽章數），搭配新增/編輯表單 — 對應 Requirement「Trigger rule management page」
- [x] 5.2 整合 CodeMirror 6 作為 DSL 表達式編輯器：設定自訂語言定義（tokenizer 對應 DSL grammar）、載入 `@codemirror/autocomplete`、`@codemirror/lint`、`@codemirror/view` tooltip extension — Decision: 前端編輯器 — CodeMirror 6 + Milkdown
- [x] 5.3 載入 `dsl-engine` WASM module，接線 CodeMirror extensions：debounce 50ms 呼叫 WASM `validate()` 更新 lint markers、Ctrl+Space 呼叫 `complete()` 顯示 autocomplete dropdown、hover 呼叫 `hover_info()` 顯示 tooltip — 對應 Requirement「DSL autocomplete suggestions」及 Requirement「DSL hover information」
- [x] 5.4 實作「測試規則」按鈕與結果顯示面板：按下後 fetch stats API → 用 WASM `evaluate()` 逐一測試每位學生 → 顯示符合/不符合表格含變數實際值，已持有徽章的學生加上提示標記 — Decision: 前端規則 dry-run 測試；Requirement「Frontend dry-run test execution」及 Requirement「Student stats aggregation API」

## 6. 前端 — 徽章說明 WYSIWYG 編輯器

- [x] [P] 6.1 在徽章管理頁面整合 Milkdown 編輯器替換 description 純文字欄位，支援 bold、italic、list、link 基本格式 — Decision: 前端編輯器 — CodeMirror 6 + Milkdown；Requirement「Milkdown WYSIWYG editor for badge description」
- [x] 6.2 實作 G2 分區塊模式：綁定 TriggerRule 時上方顯示 WASM `describe()` 產生的唯讀條件摘要區塊（含視覺區隔），下方為自由撰寫區。規則變更時自動重新產生上方區塊。無綁定規則時僅顯示自由編輯區 — 對應 Requirement「G2 dual-zone description layout」

## 7. 前端 — DSL Help Modal

- [x] [P] 7.1 在 DSL 編輯器旁新增 `[?]` help button，點擊後呼叫 WASM `get_help_content("tw")`，用現有 `window.Modal` 系統渲染格式化內容（變數表格、運算子列表、函數簽名與範例、完整表達式範例）— Decision: DSL Help Modal；Requirement「Help button on DSL editor」及 Requirement「Help content generated from Rust crate」

## 8. 後端測試

- [x] [P] 8.1 撰寫 TriggerRule CRUD API 整合測試：建立、讀取、更新、刪除規則，含 CBAC 權限驗證（教師只能管理自己班級）、表達式驗證失敗拒絕、綁定中規則刪除拒絕 — 對應 Requirement「TriggerRule CRUD API endpoints」
- [x] [P] 8.2 撰寫 badge award flow 整合測試：DSL rule 觸發頒獎、code trigger 觸發頒獎、同一 class 內兩種觸發共存、inactive rule 跳過、重複頒獎防護 — 對應 Requirement「DSL trigger evaluation in badge award flow」及 Requirement「Badge awarded automatically on trigger」
- [x] [P] 8.3 撰寫 students/stats API 測試：正常回傳、windows 參數、CBAC 權限阻擋 — 對應 Requirement「Student stats aggregation API」
- [x] [P] 8.4 撰寫 BadgeDefinition trigger_key/trigger_rule_id 互斥驗證測試 — 對應 Requirement「Mutual exclusion enforced」

## 9. Build Pipeline 與 CI

- [x] 9.1 建立 Makefile（或 justfile）封裝 `wasm-pack build` 和 `maturin develop` 命令，加入 `wasm-opt` 最佳化步驟
- [x] 9.2 更新 CI 設定：新增 Rust toolchain 安裝步驟、Rust crate 測試、WASM 編譯、PyO3 wheel 建置，設定 Cargo 快取加速
