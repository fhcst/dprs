## Context

`badges_manage.html` 使用四個 Milkdown 7.5.0 套件從 esm.sh 以裸 import 載入。由於 esm.sh 對各套件分別 bundle 內部依賴，每個套件持有獨立的 `@milkdown/ctx` 實例，導致 `commonmark` 注入的 `nodes` context 在 `Editor` 的 ctx 實例找不到，頁面進入即噴 `MilkdownError: Context "nodes" not found`，編輯器完全無法使用。

CodeMirror 6 已在 `trigger-rules.html` 透過 `<script type="importmap">` 以固定版本載入，各套件共用同一 ctx（由 importmap 保證模組只解析一次），無此問題。

## Goals / Non-Goals

**Goals:**

- 移除所有 Milkdown 依賴，以 CodeMirror 6 + `@codemirror/lang-markdown` 取代徽章說明的編輯器
- 沿用 `trigger-rules.html` 的 importmap 模式，確保版本固定、模組不重複解析
- 保持現有 `getEditorMarkdown()` / `setEditorMarkdown()` 語意不變，讓其餘 JS 邏輯零修改

**Non-Goals:**

- 不提供即時 Markdown preview（split-view 或 rendered preview）
- 不加工具列按鈕（bold、italic 快捷鍵由 CodeMirror lang-markdown keybindings 處理）
- 不修改 `trigger-rules.html` 現有的 CodeMirror 設定

## Decisions

### 使用 importmap 而非裸 CDN import

`trigger-rules.html` 已驗證：使用 `<script type="importmap">` 搭配固定版本的 esm.sh URL，可讓所有 `@codemirror/*` 套件共用同一模組實例，避免 context 衝突。Milkdown 的問題正是缺少 importmap 造成的。

`badges_manage.html` 應新增同樣格式的 importmap，加入 `@codemirror/lang-markdown` 和其 lezer parser 依賴 `@lezer/markdown`。

**替代方案**：使用 `esm.sh?bundle` 把四個套件打包成單一 URL — 已排除，bundle 模式下 esm.sh 產出的 URL 不穩定，且無法在不同頁面共用版本聲明。

### CodeMirror 版本與套件清單

與 `trigger-rules.html` 的現有版本對齊，額外新增：

| 套件 | 版本 | 用途 |
|------|------|------|
| `@codemirror/lang-markdown` | `6.3.2` | Markdown 語法解析與高亮 |
| `@lezer/markdown` | `1.4.3` | lang-markdown 的 lezer parser 依賴 |

實作者應在加入 importmap 前，至 esm.sh 確認上述版本與現有 `@codemirror/language@6.11.0` 相容。

### Editor API 封裝

以 `EditorView` 替換 Milkdown 的 `editorInstance`，封裝介面保持一致：

```
getEditorMarkdown()  → view.state.doc.toString()
setEditorMarkdown(md) → view.dispatch({ changes: { from:0, to: view.state.doc.length, insert: md } })
```

初始化：

```javascript
import { EditorView, basicSetup } from 'codemirror';
import { markdown } from '@codemirror/lang-markdown';

const view = new EditorView({
  doc: initialValue,
  extensions: [basicSetup, markdown()],
  parent: mount,
});
```

### 樣式

沿用 `trigger-rules.html` 的 `.cm-editor` CSS，調整 `min-height` 為 `120px`（與現有 `.milkdown-wrap` 一致），並加入 dark mode 支援。移除 `.milkdown-wrap` 相關 CSS。

## Risks / Trade-offs

- **使用者體驗降級**：從 WYSIWYG 變成 source mode。徽章說明通常只有 1-3 行 Markdown，影響極小；老師仍可用 `**bold**`、`- list` 語法，CodeMirror 提供即時語法高亮。
- **`@lezer/markdown` 版本鎖定**：此套件為 `@codemirror/lang-markdown` 的 peer dep，若未在 importmap 明確列出，esm.sh 可能解析不同版本。實作時需驗證。
