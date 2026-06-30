## 1. Quick Wins（無架構變更，各自獨立）

- [x] [P] 1.1 在 `base.html` 的 `<head>` 中加入 `@media (prefers-reduced-motion: reduce)` CSS 規則，覆蓋所有 `transition-duration`、`animation-duration` 為 `0.01ms`，`scroll-behavior` 設為 `auto`（Reduced motion support）
- [x] [P] 1.2 在 `base.html` 的 `<body>` 開頭加入 skip-to-content 隱藏連結（`sr-only focus:not-sr-only`），並在 `<main>` 標籤加入 `id="main-content"`（Skip-to-content link）
- [x] [P] 1.3 在 `base.html` toggleSidebar() 函式中加入 `localStorage.setItem('sidebar-collapsed', ...)` 持久化，並在頁面載入時讀取狀態還原 sidebar（Sidebar collapse state persistence）
- [x] [P] 1.4 在 `base.html:366` 的平板水平 nav 加入 `overflow-x-auto flex-nowrap scrollbar-hide` 防止溢出（Tablet horizontal nav overflow handling）
- [x] [P] 1.5 在所有 HTML 模板的 `<th>` 元素加入 `scope="col"`，為資料表格加入 `aria-label` 描述（Table accessibility markup）— 影響檔案：`admin/users_list.html`、`admin/classes_list.html`、`teacher/templates_list.html`、`community/leaderboard.html`
- [x] [P] 1.6 將 `settings.html` 中的 `emerald-*` 全部替換為 `green-*`（Consistent success color）
- [x] [P] 1.7 全站統一術語：Dashboard 的 "作業審閱" 改為 "任務審閱"，submission_review.html 的 "已確認" filter tab 改為 "已通過"（Terminology standardization）
- [x] [P] 1.8 在 `submission_review.html` 的 `{% else %}` 區塊加入空狀態 UI（圖示 + "今天沒有待審作業" 訊息）

## 2. 共用模態元件（決策 1：共用模態元件架構）

- [x] 2.1 在 `base.html` 全域 JS 中重構 `Modal` class，新增 `Modal.dialog({ title, content, onClose, onConfirm })` 方法，實作 `role="dialog"`、`aria-modal="true"`、`aria-labelledby` 綁定（Modal ARIA dialog semantics）
- [x] 2.2 在 Modal class 中實作 focus trap：modal 開啟時收集所有 focusable 元素，攔截 Tab/Shift+Tab 循環（Modal focus trap）
- [x] 2.3 在 Modal class 中實作 ESC 鍵關閉功能（Modal ESC key dismissal）和關閉後焦點還原到觸發元素（Modal focus restoration）
- [x] 2.4 在 Modal class 中實作背景滾動鎖定：modal 開啟時 `document.body.style.overflow = 'hidden'`，關閉時還原（Modal background scroll lock）
- [x] 2.5 在 Modal CSS 中加入行動端 bottom sheet 變體：`@media (max-width: 640px)` 下 modal 錨定底部，`max-height: 85vh`，`overflow-y: auto`，頂部圓角（Modal mobile bottom sheet variant）
- [x] 2.6 將 `student/dashboard.html` 的 create-class-modal 和 join-class-modal 遷移為使用新的 Modal.dialog() API
- [x] 2.7 將 `teacher/badges_manage.html` 的 badge 表單 modal 遷移為使用新的 Modal.dialog() API
- [x] 2.8 更新 `Modal.confirm()` 使用 `role="alertdialog"` 語意，確保所有現有 confirm 呼叫相容

## 3. 全站 Toast 通知系統（決策 2：全站 Toast 通知系統）

- [x] 3.1 在 `base.html` 加入全域 toast container：`<div id="toast-container" role="status" aria-live="polite" class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">`（Global toast notification container + ARIA landmarks for dynamic content）
- [x] 3.2 在 `base.html` 全域 JS 中實作 `Toast` 物件，包含 `Toast.success(msg)`、`Toast.error(msg)`、`Toast.info(msg)` 三個方法，各自有不同色彩和圖示（Toast API with three variants）
- [x] 3.3 實作 toast 自動消失邏輯（success 3 秒、error 5 秒含手動關閉按鈕）以及多 toast 垂直堆疊（Toast stacking）
- [x] 3.4 移除 `submission_review.html` 中的舊 toast 實作（`#toast-container` 和 `showToast` 函式），改用全域 Toast API

## 4. 非同步按鈕 Loading State（決策 3：非同步按鈕 Loading State）

- [x] 4.1 在 `base.html` 加入全域 form submit handler：為所有 `<form>` 的 submit 事件自動 disable submit button 並顯示 spinner SVG + "處理中..."（Form POST loading state）
- [x] 4.2 在 `base.html` 實作 `withLoading(button, asyncFunction)` 全域工具函式：disable button → 顯示 spinner → 執行 asyncFn → 還原按鈕（成功和失敗都還原），失敗時呼叫 Toast.error()（JavaScript fetch loading state utility）
- [x] [P] 4.3 在 `teacher/submission_review.html` 的 approve/reject/comment 操作改用 `withLoading()` 取代手動 disable 邏輯
- [x] [P] 4.4 在 `teacher/class_hub.html` 的 regenerateInviteCode、copyInviteCode 加入 `withLoading()` 或相應回饋
- [x] [P] 4.5 在 `teacher/badges_manage.html` 的 badge CRUD 和 award 操作加入 `withLoading()`
- [x] [P] 4.6 在 `teacher/attendance_manage.html` 的出席更正操作加入 `withLoading()`
- [x] [P] 4.7 在 `teacher/points_manage.html` 的積分扣除操作加入 `withLoading()`

## 5. 確認對話框與統一錯誤回饋

- [x] [P] 5.1 在 `community/feed.html` 的刪除貼文按鈕加入 `Modal.confirm()` 確認對話框，描述不可逆後果（Destructive action confirmation — delete post）
- [x] [P] 5.2 在 `teacher/class_hub.html` 的重新產生邀請碼加入 `Modal.confirm()` 確認對話框，警告舊邀請碼將失效（Destructive action confirmation — regenerate invite code）
- [x] [P] 5.3 在 `teacher/badges_manage.html` 的撤銷徽章和 `teacher/points_manage.html` 的扣分操作加入 `Modal.confirm()` 確認對話框（Destructive action confirmation — revoke badge, deduct points）
- [x] [P] 5.4 在 `admin/users_list.html` 的刪除使用者操作加入 `Modal.confirm()` 確認對話框（Destructive action confirmation — delete user）
- [x] 5.5 檢查所有錯誤/成功 alert banner（login.html、settings.html、submit_task.html、setup.html），確保均有 `role="alert"` 屬性（Unified error feedback pattern + ARIA landmarks for dynamic content）

## 6. 行動端導航重構（決策 4：行動端教師底部導航列）

- [x] 6.1 重寫 `base.html` 行動端底部 tab bar 的教師區塊：改為 [首頁, 審閱, 出席, 班級, 更多] 五個項目，"審閱" 連結到第一個班級的 submission_review_page，"出席" 連結到第一個班級的 attendance_manage_page（Teacher mobile bottom tab bar）
- [x] 6.2 實作教師 "更多" 按鈕：點擊開啟 bottom sheet（使用 Modal 元件），列出積分管理、徽章管理、簽到設定、Trigger Rules、個人設定連結
- [x] 6.3 重寫 `base.html` 行動端底部 tab bar 的學生區塊：改為 [首頁, 徽章, 歷程, 設定] 四個不重複項目（Student mobile bottom tab bar）
- [x] 6.4 為所有子頁面加入 breadcrumb 導航，統一使用 `{% block breadcrumb %}` 區塊（Consistent breadcrumb navigation）— 影響檔案：`student/class_history.html`、`student/learning_history.html`、`student/badges.html`、`community/leaderboard.html`、`community/feed.html`、`teacher/class_hub.html`（改用 block）

## 7. 無障礙掃描修復

- [x] 7.1 在 `submission_review.html` 的 filter tabs 加入 `role="tablist"`、`role="tab"`、`aria-selected` 屬性（Filter tabs accessibility）
- [x] [P] 7.2 在所有積分交易顯示處加入方向圖示（↑/↓ 箭頭 SVG）和 +/- 前綴文字，作為色彩以外的區分方式（Non-color status indicators）— 影響檔案：`teacher/points_manage.html`、`student/dashboard.html`（points 區塊）
- [x] [P] 7.3 在 `admin/user_form.html` 的 username 和 password 欄位加入 `autocomplete` 屬性

## 8. 前端表單即時驗證（決策 6：前端表單驗證策略）

- [x] [P] 8.1 在 `settings.html` 的新密碼欄位加入即時密碼強度指示器（弱/中/強色彩條），基於長度和字符種類計算（Password strength indicator）
- [x] [P] 8.2 在 `teacher/template_assign.html` 的日期範圍欄位加入 change 事件監聽，當 start > end 時顯示紅框和 "起始日期不可晚於結束日期" 提示（Date range cross-field validation）
- [x] [P] 8.3 在 `student/dashboard.html` 的邀請碼 input 加入自動轉大寫和 maxlength="8" 限制（Invite code format feedback）
- [x] [P] 8.4 在 `admin/user_form.html` 的 username 欄位加入 blur 事件觸發的 debounced 唯一性 API 查詢，存在時顯示 "此帳號已存在" 紅色提示，不存在時顯示綠色勾（Username uniqueness check）

## 9. Empty State 與 Dashboard 強化（決策 7：Empty State 元件統一）

- [x] 9.1 建立 `src/templates/shared/macros.html`，新增 `empty_state(icon, title, description, cta_text, cta_href)` Jinja2 macro（Unified empty state component）
- [x] 9.2 將 `student/dashboard.html` 的空班級狀態替換為 macro 呼叫：學生角色顯示 "尚未加入任何班級" + "加入班級" CTA，教師角色顯示 "尚未建立任何班級" + "建立班級" CTA
- [x] [P] 9.3 將 `student/badges.html`、`student/learning_history.html`、`student/class_history.html`、`community/feed.html` 的空狀態替換為 macro 呼叫
- [x] 9.4 在 `src/pages/router.py` 的 dashboard_page view 中新增查詢邏輯：計算教師的待審提交數和待處理加入申請數，透過 template context 傳入（Teacher dashboard pending actions）
- [x] 9.5 在 `student/dashboard.html` 的教師區塊加入待處理事項 UI：顯示 "N 份待審作業" 和 "N 個加入申請待處理" 連結，或 "所有事項已處理完畢" 勾號
- [x] 9.6 在 `src/pages/router.py` 的 dashboard_page view 中新增首次登入偵測邏輯（無提交、無班級成員、帳號建立 24 小時內），透過 template context 傳入 `is_first_login` 標記（First-time user welcome message）
- [x] 9.7 在 `student/dashboard.html` 加入首次登入歡迎卡片：學生顯示 "歡迎加入！" + 三步驟指引，教師顯示 "歡迎！開始設定您的班級" + 三步驟指引

## 10. 設計系統統一（Button visual hierarchy + Content max-width + Card styling）

- [x] [P] 10.1 修改 `submission_review.html` 的 active filter tab 樣式，從 `bg-brand-600 text-white` 改為 `bg-brand-100 text-brand-700 border-brand-300`（Button visual hierarchy）
- [x] [P] 10.2 為缺少 max-width 的頁面內容區域加入寬度限制：`submission_review.html`、`teacher/attendance_manage.html`、`teacher/points_manage.html` 加入 `max-w-5xl mx-auto`（Content max-width constraint）
- [x] [P] 10.3 將 `login.html` 的 card 從 `rounded-2xl shadow-lg` 改為 `rounded-xl shadow-lg` 統一圓角（Consistent card styling）
- [x] [P] 10.4 在 `base.html` 加入 `@media (max-width: 640px)` 的 body text size override，將 `text-sm` 在行動端提升為 `text-base`（Mobile body text minimum size）

## 11. Tailwind CSS Build Pipeline（決策 5：Tailwind CSS Build Pipeline）

- [x] 11.1 下載 Tailwind Standalone CLI 到 `tools/` 目錄，加入 `.gitignore`，並建立 `scripts/build-css.sh` 腳本（Static CSS generation）
- [x] 11.2 從 `base.html` 的 inline config 提取 Tailwind 設定到 `tailwind.config.js`，包含 brand 色彩、font family、`darkMode: 'class'`（Tailwind configuration extraction）
- [x] 11.3 設定 Tailwind CLI content 路徑為 `src/templates/**/*.html`，輸出到 `src/static/css/tailwind.css`
- [x] 11.4 修改 `base.html`：移除 `<script src="https://cdn.tailwindcss.com">` 和 inline config script，改為 `<link rel="stylesheet" href="/static/css/tailwind.css">`
- [x] 11.5 驗證遷移：比對 CDN 版本和靜態 CSS 版本的渲染結果，確保所有頁面視覺一致
- [x] 11.6 更新 Dockerfile 在 build stage 加入 CSS 建構步驟

## 12. 觸控目標與編輯器行動端優化

- [x] [P] 12.1 提升所有互動元素的最小觸控區域至 44x44px：`community/feed.html` 的刪除按鈕（從 `p-1.5` 改為 `p-2.5 min-w-[44px] min-h-[44px]`）、反應按鈕（增加 `py-2`）（Touch target minimum size）
- [x] [P] 12.2 修改 `student/submit_task.html` 的 Toast UI Editor 初始化：偵測 `window.innerWidth < 640` 時使用 `previewStyle: 'tab'`，否則使用 `'vertical'`（Toast UI Editor mobile preview mode）
