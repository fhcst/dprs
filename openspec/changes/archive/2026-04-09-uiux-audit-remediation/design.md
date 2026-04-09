## Context

此系統使用 FastAPI + Jinja2 server-side rendering，搭配 Tailwind CSS Play CDN（runtime JIT）和 vanilla JavaScript。27 個 HTML 模板分屬 Student、Teacher、Admin、Community 四個類別，全部繼承 `src/templates/shared/base.html`。目前沒有前端建構工具（無 npm、webpack、vite），所有第三方依賴透過 CDN 載入。

關鍵約束：
- 不引入前端框架（React/Vue/Svelte）— 維持 Jinja2 + vanilla JS 架構
- 後端 Python 邏輯不做大幅修改（唯一例外：Dashboard route 需新增待處理事項查詢）
- 所有變更必須向後相容，不能中斷現有功能
- 系統使用 `fastapi-webpage` 自訂套件處理模板渲染

## Goals / Non-Goals

**Goals:**

- 達成 WCAG 2.1 AA 基本合規（消除所有 CRITICAL 等級的無障礙違規）
- 教師在行動裝置上能完成核心工作流（審閱提交、管理出席）
- 所有使用者操作有明確的回饋（loading、success、error）
- 建立可重用的共用元件（modal、toast、loading button）減少各模板重複實作
- Tailwind CSS 從 runtime CDN 遷移至 build-time 靜態 CSS

**Non-Goals:**

- 不建立即時推送通知（WebSocket / SSE）
- 不替換 Badge emoji 為 SVG 圖示系統
- 不實作批量審閱功能
- 不引入前端框架或 SPA 架構
- 不重寫後端 API

## Decisions

### 決策 1：共用模態元件架構

**選擇**：在 `base.html` 的全域 JS 中擴展現有 `Modal` class，新增 `Modal.dialog(options)` 方法。

**替代方案**：
- Web Component (`<app-modal>`) — 需要 template/slot 語法，與 Jinja2 模板系統整合較複雜
- 每個模板維持獨立 modal — 現狀，導致 5+ 處重複程式碼且行為不一致

**理由**：現有 `Modal.confirm()` / `Modal.alert()` 已在 `base.html` 中，擴展此 class 是最低衝擊路徑。新增 `Modal.dialog({ title, content, onClose })` 用於自訂內容。所有 modal 實例共用 focus trap、ESC 關閉、aria 屬性。

**實作要點**：
- Focus trap：在 `Modal.show()` 中收集 modal 內所有 `focusable` 元素，攔截 Tab/Shift+Tab
- 焦點還原：在 `Modal.show()` 前記錄 `document.activeElement`，`Modal.hide()` 後還原
- 行動端 bottom sheet：新增 CSS class `.modal-mobile-sheet`，在 `@media (max-width: 640px)` 下以 bottom-anchored 樣式呈現
- 背景滾動鎖定：modal 開啟時 `document.body.style.overflow = 'hidden'`

### 決策 2：全站 Toast 通知系統

**選擇**：從 `submission_review.html` 提取 toast 邏輯到 `base.html`，成為全域 `Toast` 物件。

**替代方案**：
- 引入第三方 toast 庫（如 toastify-js）— 增加 CDN 依賴
- 保持每個頁面自行實作 — 現狀，只有 1/27 模板有 toast

**理由**：現有 toast 實作已經可用，只需提取並增加 ARIA 支援。

**實作要點**：
- 全域 container 在 `base.html` 渲染：`<div id="toast-container" role="status" aria-live="polite" class="fixed top-4 right-4 z-50">`
- API：`Toast.success(msg)` / `Toast.error(msg)` / `Toast.info(msg)`
- 自動消失：success 3 秒、error 5 秒（或手動關閉）
- 堆疊：多個 toast 垂直堆疊，`space-y-2`

### 決策 3：非同步按鈕 Loading State

**選擇**：兩層策略 — (1) form POST 用全域 `onsubmit` handler；(2) JS fetch 操作用 `withLoading(btn, asyncFn)` 工具函式。

**替代方案**：
- 只處理 JS fetch（忽略 form POST）— 遺漏簽到、登入等關鍵操作
- 使用 CSS-only loading（`cursor: wait`）— 不夠明確，使用者可能認為按鈕仍可點擊

**實作要點**：
- Form POST handler（`base.html` 全域）：所有 `<form>` 的 `submit` 事件自動 disable submit button 並顯示 spinner
- `withLoading(btn, asyncFn)` 工具函式：disable button → 替換文字為 spinner + "處理中..." → 執行 asyncFn → 還原（無論成功失敗）
- Spinner HTML：`<svg class="animate-spin w-4 h-4 inline-block" ...>`

### 決策 4：行動端教師底部導航列

**選擇**：依角色條件渲染不同的底部導航項目。教師看到 [首頁, 審閱, 出席, 班級, 更多]，學生看到 [首頁, 徽章, 歷程, 設定]。

**替代方案**：
- 單一導航列 + hamburger menu — 增加一次點擊才能到達功能
- 不使用底部導航（教師只用 sidebar）— 現狀，行動端完全無法操作

**實作要點**：
- 教師 "更多" 按鈕開啟 bottom sheet（使用決策 1 的 Modal 元件），列出：積分管理、徽章管理、簽到設定、Trigger Rules
- 教師 "審閱" 直接連結到第一個班級的 `submission_review_page`（如有多班級，進入後可切換）
- 教師 "出席" 直接連結到第一個班級的 `attendance_manage_page`
- 教師 "班級" 連結到 Dashboard（班級列表在 Dashboard）

### 決策 5：Tailwind CSS Build Pipeline

**選擇**：使用 Tailwind CSS Standalone CLI（不需要 Node.js/npm），透過 Makefile 或 shell script 執行。

**替代方案**：
- npm + tailwindcss package — 引入 Node.js 生態系，增加專案複雜度
- 維持 Play CDN — 現狀，效能差且不適合生產環境
- UnoCSS — 需要 Node.js，學習曲線

**理由**：Tailwind Standalone CLI 是單一二進位檔，不需要 Node.js。可透過 `curl` 下載到 `tools/` 目錄，用 Makefile target 或 script 執行。符合專案現有的 Python + Docker 工具鏈。

**實作要點**：
- 下載 Tailwind Standalone CLI 到 `tools/tailwindcss`（gitignore）
- 建立 `tailwind.config.js`（從 `base.html` 內嵌配置提取）
- 輸入：`src/templates/**/*.html`
- 輸出：`src/static/css/tailwind.css`
- `base.html` 改為 `<link rel="stylesheet" href="/static/css/tailwind.css">`
- 開發模式：`tailwindcss --watch`
- Docker build：在 Dockerfile 中新增 CSS build step

### 決策 6：前端表單驗證策略

**選擇**：純 vanilla JS 驗證，不引入驗證庫。每個需要驗證的表單在其模板的 `{% block scripts %}` 中加入驗證邏輯。

**替代方案**：
- Zod + 前端驗證庫 — 需要 build step 和 bundler
- HTML5 Constraint Validation API only — 功能有限，無法做跨欄位驗證

**實作要點**：
- 密碼強度：基於長度 + 字符種類數計算 weak/medium/strong，即時更新色彩指示條
- 日期範圍：`start_date` 的 `change` 事件觸發與 `end_date` 比較，不合法時加紅框 + 提示文字
- 邀請碼：`input` 事件自動轉大寫、限制長度
- Username 唯一性：`blur` 事件觸發 debounced API 查詢

### 決策 7：Empty State 元件統一

**選擇**：建立 Jinja2 macro `{% macro empty_state(icon, title, description, cta_text, cta_href) %}`，所有需要空狀態的模板引入此 macro。

**替代方案**：
- 每個模板各自設計 — 現狀，風格不一致
- Jinja2 include（`{% include "shared/empty_state.html" %}`）— 不如 macro 靈活（無法傳參數）

**實作要點**：
- 新增 `src/templates/shared/macros.html`
- macro 接受 `icon`（SVG name）、`title`、`description`、`cta_text`（可選）、`cta_href`（可選）
- 預設樣式：虛線邊框 card + 圖示 + 標題 + 描述 + CTA 按鈕
- 替換所有現有 empty state 為此 macro

## Risks / Trade-offs

- **[Tailwind 遷移期間樣式斷裂]** → 遷移步驟：先產生靜態 CSS 與 CDN 並存，驗證無差異後再移除 CDN。在 CI 中加入 CSS diff 檢查。
- **[共用元件破壞現有模板]** → 逐個模板遷移，每個遷移單獨測試。不做一次性全域替換。
- **[表單驗證誤擋合法輸入]** → 前端驗證僅為輔助提示（加紅框 + 訊息），不阻止 submit。後端驗證仍為最終防線。
- **[行動端導航項目過多]** → 教師底部列限制 5 個項目，其餘收入 "更多" sheet。
- **[prefers-reduced-motion 覆蓋正常動畫]** → 使用 `0.01ms` 而非 `0ms`，確保 JS 的 `transitionend` 事件仍會觸發。
