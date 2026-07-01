## 1. 移除 Milkdown 並新增 CodeMirror importmap

- [x] 1.1 移除 `badges_manage.html` `<script type="module">` 頂端的四個 Milkdown 裸 import（`@milkdown/core`、`@milkdown/preset-commonmark`、`@milkdown/theme-nord`、`@milkdown/utils`）
- [x] 1.2 在 `badges_manage.html` 的 `{% block head_extra %}` 中新增 `<script type="importmap">`，遵循「使用 importmap 而非裸 CDN import」決策，加入與 trigger-rules.html 版本一致的 CodeMirror 套件，並依「CodeMirror 版本與套件清單」決策額外新增 `@codemirror/lang-markdown@6.3.2` 和 `@lezer/markdown@1.4.3`

## 2. 更新 CSS 樣式

- [x] 2.1 移除 `{% block head_extra %}` 中的 `.milkdown-wrap` 相關 CSS 區塊（含 dark mode 變體）及 `.g2-auto-zone` 以外的 Milkdown 相關規則（依「樣式」決策）
- [x] 2.2 新增 `.cm-editor` CSS 規則：`min-height: 120px`、`padding: 12px 16px`、dark mode `focus` ring（`outline: 2px solid rgb(139 92 246)`），與 trigger-rules.html 的樣式保持一致（依「樣式」決策）

## 3. 重寫編輯器 JS（CodeMirror 6 Markdown editor for badge description）

- [x] 3.1 依「Editor API 封裝」決策，以 `EditorView` + `basicSetup` + `markdown()` 重寫原「Milkdown WYSIWYG editor for badge description」實作（`initMilkdown` 函式改名為 `initCodeMirror`），掛載至 `#milkdown-editor` container；原 `editorInstance` 變數改為 `view`（`EditorView` 實例）
- [x] 3.2 更新 `getEditorMarkdown()`：改為 `return view ? view.state.doc.toString() : ''`
- [x] 3.3 更新 `setEditorMarkdown(md)`：改為 `view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: md } })`；若 view 未初始化則 fallback 至 `initCodeMirror(md)`
- [x] 3.4 將頁面底部的 `await initMilkdown('')` 呼叫改為 `await initCodeMirror('')`，確認 `editBadge()`、cancel edit、`setEditorMarkdown()` 的呼叫點全部指向更新後的實作

## 4. UI/UX 改善與 Modal HTML 修正

- [x] 4.1 `badges_manage.html` form 標題列改為 flex 排版，加入 `(?)` 圓形說明按鈕（`aria-label`、`cursor-pointer`、`transition-colors`，與 trigger-rules.html 一致）
- [x] 4.2 `badges_manage.html` 新增 CodeMirror gutter CSS（`.cm-gutters { background: transparent }`，配合容器背景；gutter 文字色 light `#9ca3af` / dark `#6b7280`）
- [x] 4.3 `badges_manage.html` 說明 modal JS：使用 `Modal.alertHtml()` 顯示觸發來源說明（手動/trigger_key/DSL）、內建 trigger_key 格式表（`checkin_streak_N`、`submit_N`）、Markdown 語法速查表與範例
- [x] 4.4 `base.html` 新增 `Modal.alertHtml(htmlMsg, onClose)` 方法：以 `innerHTML` 設定內容（僅供內部寫死字串）、自動切換 modal 至 `max-w-2xl` + `overflow-y-auto max-h-[85vh]`、關閉後還原原始尺寸
- [x] 4.5 `trigger-rules.html` 兩處 DSL help modal 由 `Modal.alert(htmlContent)` 改為 `Modal.alertHtml(htmlContent)`，修正 HTML 跳脫問題

## 5. 驗證（對應 badge-description-editor 需求場景）

- [x] 5.1 開啟徽章管理頁面，確認瀏覽器 DevTools console 無 uncaught error，且 CodeMirror 編輯器正確渲染於表單中（對應「Editor initializes without JavaScript error」場景）
- [x] 5.2 點擊現有徽章的編輯按鈕，確認 CodeMirror 編輯器顯示該徽章的既有說明文字（對應「Edit mode pre-fills editor content」場景）
- [x] 5.3 輸入 `**粗體**` 後儲存新徽章，再次開啟編輯確認 description 欄位儲存的是 Markdown 原始文字而非 HTML（對應「Badge description stored as Markdown」場景）
- [x] 5.4 點擊表單 `(?)` 按鈕，確認 modal 正確以 HTML 渲染（表格顯示正常、非原始標籤字串）
<!-- Note: 4.1-4.3 are manual browser verification steps. Automated spec coverage provided by test_badges_manage_page_uses_codemirror_importmap in test_pages.py -->
