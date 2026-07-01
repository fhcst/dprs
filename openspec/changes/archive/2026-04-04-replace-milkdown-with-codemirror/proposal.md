## Why

`badges_manage.html` 使用 Milkdown 7.5.0 作為徽章說明的 WYSIWYG 編輯器，但因為從 esm.sh 分別載入四個 Milkdown 套件，導致各套件各自 bundle 一份 `@milkdown/ctx`，Context "nodes" 無法跨實例注入，編輯器一進入頁面即崩潰。此外，近期多起 CDN 供應鏈攻擊事件（npm → jsDelivr/unpkg/esm.sh）顯示直接從 public CDN 載入非必要新套件的風險持續升高。

## What Changes

- 移除 `badges_manage.html` 中所有 Milkdown 相關 import（`@milkdown/core`、`@milkdown/preset-commonmark`、`@milkdown/theme-nord`、`@milkdown/utils`）
- 改用 CodeMirror 6 作為徽章說明欄位的 Markdown 編輯器，並沿用 `trigger-rules.html` 已有的 esm.sh import map 模式（固定版本、單一 CDN 來源）
- CodeMirror 6 加入 `@codemirror/lang-markdown` 支援，提供 Markdown 語法高亮與基本編輯體驗（非 WYSIWYG，而是 source mode + syntax highlighting）
- 更新 `badge-description-editor` spec：將「WYSIWYG（Milkdown）」需求改為「Markdown source mode 編輯器（CodeMirror 6）」
- `getEditorMarkdown()` / `setEditorMarkdown()` 接口維持不變，其餘 JS 邏輯（表單提交、觸發來源切換、G2 自動摘要區）不受影響
- `badges_manage.html` 表單標題列新增 `(?)` 說明按鈕，點擊後彈出 modal 說明觸發來源類型、內建 trigger_key 格式（`checkin_streak_N`、`submit_N`）與 Markdown 語法速查
- `base.html` 新增 `Modal.alertHtml(html)` 方法：使用 `innerHTML` 渲染富文字 HTML，並自動將 modal 展開至 `max-w-2xl` + `overflow-y-auto`；此方法僅供內部寫死字串使用，不接受使用者輸入
- `trigger-rules.html` 的 DSL 說明 modal 由 `Modal.alert(htmlContent)` 改為 `Modal.alertHtml(htmlContent)`，修正 HTML 被跳脫成純文字的顯示問題

## Non-Goals

- 不提供即時 Markdown preview（側欄 split view）
- 不加入 Milkdown 以外的其他 WYSIWYG 套件
- 不修改後端 API 或資料庫結構

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `badge-description-editor`：將 Milkdown WYSIWYG 需求改為 CodeMirror 6 Markdown source-mode 編輯器；移除 WYSIWYG 渲染的要求，改為語法高亮即時提示；其餘行為（儲存 Markdown 文字、支援 bold/italic/list/link/code）不變

## Impact

- Affected specs: `badge-description-editor`（需求層級變更）
- Affected code:
  - `src/templates/teacher/badges_manage.html`（Milkdown import 替換、CodeMirror importmap、gutter CSS、說明按鈕與 modal）
  - `src/templates/shared/base.html`（新增 `Modal.alertHtml()` 方法）
  - `src/templates/teacher/trigger-rules.html`（DSL help modal 改用 `Modal.alertHtml()`）
- Removed dependencies: `@milkdown/core`, `@milkdown/preset-commonmark`, `@milkdown/theme-nord`, `@milkdown/utils`（均來自 esm.sh）
- Added dependencies: `@codemirror/lang-markdown`（透過 esm.sh import map，與 trigger-rules.html 同版本管理策略）
