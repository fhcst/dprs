## Context

目前成就系統的觸發條件由開發者以 Python `BadgeTrigger` Protocol 實作，透過 `ExtensionRegistry` 在 `main.py` 啟動時註冊。教師只能建立 `BadgeDefinition` 並綁定已存在的 `trigger_key`，無法自行定義觸發邏輯。

本變更引入 DSL 表達式系統，讓教師在 Web UI 上直接撰寫觸發規則。DSL 引擎以 Rust 實作，單一 crate 編譯為 WASM（前端）與 PyO3（後端），確保行為一致。

相關現有 specs：`badge-system`、`extension-registry`、`permission-system`、`modal-system`。

## Goals / Non-Goals

**Goals:**

- 教師可在 UI 上用表達式語言撰寫觸發規則，無需開發者介入
- 前端即時驗證、autocomplete、hover 提示、dry-run 測試
- 前後端使用同一套 Rust 引擎，零行為分歧
- DSL 在嚴格沙箱中運行：只讀、class-scoped、白名單函數、無賦值/迴圈
- 現有 Python Protocol BadgeTrigger 機制完整保留
- 徽章說明支援 WYSIWYG Markdown，自動產生條件摘要

**Non-Goals:**

- 不取代 Python Protocol — 開發者程式碼注入完整保留
- 不提供 DSL 規則版本管理或 diff
- 不建立獨立 LSP server — 透過 WASM export + CodeMirror extensions 實現
- 不支援 DSL 中的資料寫入、跨 class 存取、任意函數呼叫

## Decisions

### Decision: DSL 語法設計 — S2 表達式語言

採用類 SQL WHERE 的表達式語法，而非自然語言或 YAML 結構化。

**語法規格：**

```
內建變數（class-scoped，對當前觸發學生求值）：
  checkin_count: int          — 總打卡次數
  checkin_streak: int         — 連續打卡天數
  submission_count: int       — 總繳交次數
  points: int                 — 目前點數
  badge_count: int            — 已獲得徽章數
  event.type: string          — "checkin" | "submission" | "manual"
  event.occurred_at: datetime — 事件發生時間

運算子：
  比較: ==  !=  >  >=  <  <=
  邏輯: AND  OR  NOT
  分組: ( )

字面值：
  數字: 7, 3.5
  字串: "checkin", "submission"
  布林: true, false

內建函數（白名單制）：
  count(submissions, last_N_days) → int  — 最近 N 天繳交次數
  count(checkins, last_N_days) → int     — 最近 N 天打卡次數
  day_of_week(event.occurred_at) → int   — 0(一) ~ 6(日)
```

**安全限制：** 無賦值語句、無迴圈、無任意函數呼叫、函數白名單制。DSL 引擎接收預先由 service 層組好的 context dict，本身沒有任何查詢能力。

**替代方案：** S1 自然語言（parser 難寫、國際化麻煩）、S3 YAML 結構化（冗長、不像寫規則）。S2 在 parser 複雜度、教師理解度、LSP 支援度之間取得平衡。

### Decision: Rust 單一 crate 雙編譯目標（R1 架構）

`crates/dsl-engine/` 作為核心 crate，提供以下 public API：

```
parse(source: &str) → Result<Ast, Vec<ParseError>>
validate(source: &str) → Vec<Diagnostic>
evaluate(source: &str, context: &EvalContext) → Result<bool, EvalError>
complete(source: &str, cursor_pos: usize) → Vec<Suggestion>
hover_info(source: &str, cursor_pos: usize) → Option<TypeInfo>
describe(source: &str, locale: &str) → Result<String, ParseError>
get_help_content(locale: &str) → HelpContent
```

**WASM 目標：** 使用 `wasm-pack` 編譯，產出 npm package 供前端使用。所有 API 透過 `wasm-bindgen` 導出為 JS 可呼叫函數。

**PyO3 目標：** 使用 `maturin` 編譯為 Python wheel。Python 後端透過 `import dsl_engine` 直接呼叫 native binding，在 `evaluate_triggers_for_event()` 中使用。

**Parser 實作：** 使用 `pest` PEG parser generator 定義文法。PEG 文法可直接轉換為 CodeMirror 的 syntax highlighting 規則。

**替代方案：** R2（前端 WASM + 後端 Python 重新實作）可降低 build 複雜度，但有行為分歧風險。選擇 R1 是為了消除技術債。

### Decision: 觸發規則與徽章分離管理（F2 架構）

**TriggerRule model（新 MongoDB collection）：**

```python
class TriggerRule(Document):
    class_id: str                    # CBAC 隔離
    name: str                        # 規則顯示名稱
    expression: str                  # DSL 表達式
    description_override: Optional[str]  # 教師自訂描述（覆寫自動產生）
    is_active: bool = True           # 啟用/停用
    created_by: str                  # 建立者 user_id
    created_at: datetime
    updated_at: datetime

    class Settings:
        name = "triggerrules"
```

**BadgeDefinition model 修改：**

新增 `trigger_rule_id: Optional[str]` 欄位，與現有 `trigger_key` 互斥。驗證邏輯：`trigger_key` 和 `trigger_rule_id` 不可同時有值。

**評估流程合併：**

`evaluate_triggers_for_event()` 依序處理兩種觸發來源：
1. `trigger_key` 有值 → 從 ExtensionRegistry 取得 BadgeTrigger，呼叫 `trigger.evaluate()`
2. `trigger_rule_id` 有值 → 從 DB 載入 TriggerRule，呼叫 `dsl_engine.evaluate()`
3. 兩者皆無 → 手動頒發，跳過

**替代方案：** F1（統一入口、三模式切換）更簡單，但一條規則只能綁一個徽章，彈性不足。F2 允許一對多綁定。

### Decision: 前端編輯器 — CodeMirror 6 + Milkdown

**規則編輯器：** CodeMirror 6，搭配 WASM 整合：
- `@codemirror/lang-*` — 使用自訂語言定義（lezer tokenizer 或 `StreamLanguage`）
- `@codemirror/autocomplete` — 接 WASM `complete()` 回傳 Suggestion
- `@codemirror/lint` — 接 WASM `validate()` 回傳 Diagnostic
- `@codemirror/view` (tooltip) — 接 WASM `hover_info()` 回傳 TypeInfo
- debounce 50ms 觸發 WASM parse + validate

**徽章說明編輯器：** Milkdown（ProseMirror 核心），G2 分區塊模式：
- 上方鎖定區塊：自動由 WASM `describe()` 產生的條件摘要 Markdown
- 下方自由區塊：教師自行撰寫的補充說明
- 綁定的 `trigger_rule_id` 變更時，上方區塊自動同步更新

**替代方案：** Monaco Editor 功能更強但體積 ~2MB，不適合 template-based 前端和行動裝置。Tiptap 比 Milkdown 重且功能超出需求。

### Decision: 前端規則 dry-run 測試

**Stats API endpoint：** `GET /api/classes/{class_id}/students/stats`
- 權限：`require_permission(MANAGE_OWN_CLASS)` + `can_manage_class()` CBAC 驗證
- 回傳：該班所有學生的聚合統計值（`checkin_count`, `checkin_streak`, `submission_count`, `points`, `badge_count`）
- 對 `last_N_days` 函數：額外回傳時間窗口預計算欄位（由 query parameter 指定窗口大小）

**前端 dry-run 流程：**
1. 教師按「測試規則」→ 呼叫 stats API 取得學生資料
2. 對每位學生，用 WASM `evaluate()` 求值
3. 顯示符合/不符合清單，包含各變數實際值
4. 已持有該徽章的學生加上提示標記

**安全性：** Stats API 只回傳聚合統計值（非原始資料），CBAC 確保只看到自己班的資料。

### Decision: DSL Help Modal

Help Modal 內容由 Rust crate 的 `get_help_content(locale)` 生成 JSON，包含：
- `variables`: 所有內建變數的名稱、型別、說明
- `operators`: 所有運算子的符號與說明
- `functions`: 所有內建函數的簽名、說明、範例
- `examples`: 完整規則範例

前端用現有的 `window.Modal` 系統（modal-system spec）渲染。繁中翻譯以 `locale/tw.json` 提供。

### Decision: DSL 安全沙箱與 CBAC 整合

**沙箱邊界：**

DSL 引擎的 `evaluate()` 接收 `EvalContext` struct，由 Python service 層在呼叫前組裝：
- service 層查詢 MongoDB，只取該 class_id 的資料（CBAC 已過濾）
- 將聚合結果填入 `EvalContext` 的固定欄位
- DSL 引擎只對 `EvalContext` 做條件運算，無法主動查詢

**白名單存取：**
- ✅ `checkin_count`, `checkin_streak`, `submission_count`, `points`, `badge_count`, `event.*`
- 🚫 `user.permissions`, 跨 class 資料, 其他學生資料, DB 寫入, 系統設定, JWT/auth 資料

**API 層驗證：**
- TriggerRule CRUD：`require_permission(MANAGE_OWN_CLASS)` + `can_manage_class()` CBAC
- 建立/更新規則時，後端用 PyO3 `validate()` 驗證 DSL 語法
- 拒絕不合法的表達式，回傳具體錯誤訊息

## Risks / Trade-offs

- [Rust build 複雜度] 引入 Rust toolchain（wasm-pack + maturin）增加 CI/CD 複雜度 → 透過 Makefile/justfile 封裝 build 命令，CI 使用快取減少編譯時間
- [PyO3 平台相容性] PyO3 wheel 需要每個目標平台編譯 → 使用 maturin 的 cross-compilation 支援，Docker 部署環境固定為 linux/amd64
- [WASM bundle 大小] DSL engine WASM 可能增加前端載入時間 → 使用 `wasm-opt` 最佳化，lazy load（只在規則編輯頁面載入），預期 gzip 後 < 100KB
- [CodeMirror + Milkdown 共存] 同頁面載入兩個編輯器框架 → 兩者不同時出現在同一頁面（規則管理頁用 CodeMirror，徽章管理頁用 Milkdown），無衝突
- [DSL 表達力天花板] 教師可能需要超出 DSL 能力的複雜條件 → 提供「手動頒發」作為 fallback，複雜條件仍可請開發者寫 Python Protocol
