## Context

目前 `send_task_embed()` 函式使用 hardcoded 格式產生 Discord embed 訊息：title 直接使用任務名稱、description 截取前 200 字元、footer 固定為「每日訓練提交系統」。教師無法根據班級風格客製化訊息內容。

現有架構：
- **Class model**（`src/core/classes/models.py`）：Beanie Document，已有 `discord_webhook_url` 欄位
- **send_task_embed()**（`src/integrations/discord/service.py`）：接受 `webhook_url`、`task_name`、`description`、`date` 四個參數，直接組裝 embed payload
- **任務派發流程**：教師在 `template_assign.html` 表單勾選「同步到 Discord」後，router 呼叫 `send_task_embed()`

## Goals / Non-Goals

**Goals:**

- 讓教師能在班級層級設定 Discord 訊息模板（title、description、footer）
- 讓教師能在派發任務時覆蓋班級預設模板
- 提供 `{variable}` 變數插值機制，讓模板內容動態填入任務資訊
- 提供說明 Modal，列出可用變數與 Discord Markdown 語法速查

**Non-Goals:**

- 不做即時預覽（Preview）功能
- 不支援自訂 embed color 或 embed image
- 不做模板版本歷史或回復功能
- 不處理多語系模板（目前僅支援單一模板）

## Decisions

### 使用嵌套 dict 儲存模板欄位而非獨立 collection

在 Class model 中新增 `discord_template` 嵌套欄位（embedded dict），包含 `title_format`、`description_template`、`footer_text` 三個字串欄位，預設皆為空字串。

**替代方案**：建立獨立 `DiscordTemplate` collection，以 `class_id` 關聯。
**選擇理由**：模板與班級為 1:1 關係，資料量小，嵌套欄位避免額外 query，且與現有 `discord_webhook_url` 欄位風格一致。MongoDB embedded document 是此場景的慣用做法。

### 採用三層 fallback 解析策略

模板解析順序：**任務層級覆蓋 > 班級預設 > 系統預設**。每個欄位獨立 fallback：

| 欄位 | 系統預設值 |
|------|-----------|
| title_format | `{task_name} — {date}` |
| description_template | 截取任務描述前 200 字（現有行為） |
| footer_text | `site_name` 設定值（現為「每日訓練提交系統」） |

空字串視為「未設定」，觸發 fallback。

**替代方案**：僅支援班級層級模板，不允許任務層級覆蓋。
**選擇理由**：三層 fallback 提供最大彈性，且向後相容——未設定模板時行為與現有完全一致。

### 使用 str.format_map() 搭配 SafeDict 實作變數插值

建立 `SafeDict` 類別（繼承 `dict`，覆寫 `__missing__` 回傳原始 placeholder），使用 Python 內建 `str.format_map()` 進行變數替換。

可用變數：
- `{task_name}` — 任務名稱
- `{date}` — 派發日期
- `{class_name}` — 班級名稱
- `{description}` — 任務描述（完整文字）

**替代方案**：使用 Jinja2 模板引擎或正則替換。
**選擇理由**：`str.format_map()` 是 Python 標準庫功能，零依賴、效能好。`SafeDict` 確保無效變數不會拋出 `KeyError`，而是保留原始文字（如 `{unknown}` 原樣輸出），同時記錄 warning log。相較 Jinja2 避免引入額外依賴與 XSS 風險；相較正則替換，format_map 更直觀且支援標準 Python 格式化語法。

### 在 send_task_embed() 中整合模板解析邏輯

擴充 `send_task_embed()` 簽名，新增 optional 參數：
- `title_override: str | None = None`
- `description_override: str | None = None`
- `footer_override: str | None = None`
- `class_name: str | None = None`

函式內部執行三層 fallback + 變數插值，最後組裝 embed payload。這保持現有呼叫點不需修改（所有新參數皆為 optional，預設值觸發原有行為）。

**替代方案**：獨立建立 `TemplateRenderer` 類別，send_task_embed 只接受已渲染的文字。
**選擇理由**：目前模板邏輯簡單（三個欄位 + format_map），不需要獨立類別。將解析邏輯放在 send 函式內可確保 Discord embed 限制（title 256 字元、description 4096 字元、footer 2048 字元）在同一處驗證與截斷。未來若模板邏輯變複雜，可再抽出。

### 新增 PATCH API 設定班級模板

新增 `PATCH /classes/{class_id}/discord-template` endpoint，接受 JSON body：

```json
{
  "title_format": "...",
  "description_template": "...",
  "footer_text": "..."
}
```

所有欄位皆為 optional；未提供的欄位不更動。空字串表示清除該欄位（回到 fallback）。此 endpoint 複用現有 `can_manage_class` 權限檢查。

**替代方案**：將模板欄位整合到現有 `PATCH /classes/{class_id}` endpoint。
**選擇理由**：獨立 endpoint 職責更清晰，避免與現有 class 更新邏輯混淆，也方便未來前端單獨呼叫。

### Discord embed 欄位長度限制與截斷

在組裝 embed payload 前，對各欄位進行截斷：
- title：截斷至 256 字元（Discord API 限制）
- description：截斷至 4096 字元（Discord API 限制）
- footer：截斷至 2048 字元（Discord API 限制）

截斷時在末尾加上 `...` 提示已截斷。此邏輯在 `send_task_embed()` 內部處理。

## Risks / Trade-offs

- **[風險] 變數插值中的使用者輸入可能包含惡意內容** → 因為 Discord embed 不執行 HTML/JS，且 `str.format_map()` 僅做字串替換不會執行程式碼，安全風險低。但 description 內容送往 Discord API 前不做額外 sanitization（Discord 本身處理 Markdown rendering）。
- **[風險] `{` 或 `}` 單獨出現在模板中可能導致 format_map 拋出 ValueError** → SafeDict 僅處理 `KeyError`；若模板有未配對大括號，需在 format_map 外層加 try-except 捕捉 ValueError，fallback 為原始模板文字並記錄 warning。
- **[取捨] 嵌套欄位無法獨立查詢** → 目前無此需求，若未來需要根據模板內容搜尋班級，可加 MongoDB index。
- **[取捨] 未提供即時預覽** → 降低實作複雜度，教師可透過實際派發測試任務來確認效果。

## Migration Plan

- `discord_template` 欄位預設為 `None`（MongoDB 不需要 schema migration）
- 現有班級的 `discord_template` 為 `None`，`send_task_embed()` 的 fallback 邏輯確保行為與現有完全一致
- 無需資料遷移腳本；新欄位在首次設定時才寫入

## Open Questions

（無——設計討論中已解決所有主要問題）
