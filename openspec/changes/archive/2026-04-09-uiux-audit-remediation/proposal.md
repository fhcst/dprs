## Why

2026-04-08 的全面 UI/UX 審查（`docs/uiux-audit/20260408/`）識別出 35 個問題：5 個 CRITICAL、12 個 HIGH、10 個 MEDIUM、8 個 LOW。最關鍵的缺陷包括：WCAG 2.1 AA 無障礙違規（零 `prefers-reduced-motion`、無 skip-to-content、模態缺少 ARIA/focus trap）、教師手機端完全無法進入班級管理功能、89% 的非同步操作缺乏 loading 回饋、以及 Tailwind Play CDN 用於生產環境。在教育平台中，這些問題直接影響到有身心障礙的學生、需要在課堂中使用手機操作的教師、以及系統的可靠性。

## What Changes

### 無障礙 (Accessibility)
- 全站新增 `prefers-reduced-motion: reduce` 媒體查詢
- `base.html` 加入 skip-to-content 連結
- 所有模態元件加入 `role="dialog"`、`aria-modal="true"`、focus trap、ESC 關閉
- 錯誤/成功訊息加入 `role="alert"` 和 `aria-live`
- 表格加入 `scope="col"`、`caption` 等無障礙標記
- 所有狀態指示器補充非色彩的區分方式（圖示 + 文字）
- 篩選標籤加入 `role="tablist"` / `role="tab"` / `aria-selected` 語意

### 導航與行動端 (Navigation & Mobile)
- 重新設計教師行動端底部導航列（新增審閱、出席、班級入口）
- 修復學生底部導航列的重複項目
- Sidebar collapse 狀態持久化到 localStorage
- 平板水平導航加入 `overflow-x-auto`
- 統一所有頁面的 breadcrumb 導航（使用 `{% block breadcrumb %}`）

### 共用元件 (Shared Components)
- 建立全站共用模態元件（含無障礙支援 + 行動端 bottom sheet 變體）
- 建立全站 Toast 通知系統（從 `submission_review.html` 提取並擴展）
- 建立非同步按鈕 loading state 工具函式

### 互動回饋 (Interaction & Feedback)
- 所有非同步操作加入 loading state（按鈕 disable + spinner）
- 關鍵表單加入即時前端驗證（密碼強度、日期範圍交叉檢驗、邀請碼格式）
- 破壞性操作加入確認對話框（刪除貼文、重新產生邀請碼、撤銷徽章、扣分）
- 統一錯誤回饋模式：表單用 inline banner、非同步操作用 toast

### 設計系統 (Design System)
- 統一按鈕樣式（區分主要 CTA 與 active tab 的視覺語意）
- 設計並統一 empty state 元件（圖示 + 說明 + CTA）
- 內容寬度限制（`max-w-5xl` 或 `max-w-3xl`）
- 行動端 body text 提升為 `text-base`（16px）
- 統一 card padding 和 success 色彩（`emerald` → `green`）

### 效能 (Performance)
- Tailwind CSS 改為 build-time 編譯（替換 Play CDN）
- Toast UI Editor 行動端改用 `tab` 預覽模式
- 觸控目標大小提升至 44x44px 最低標準

### 內容與引導 (Content & Onboarding)
- Dashboard empty state 依角色顯示不同引導（學生：加入班級；教師：建立班級）
- Dashboard 教師端新增「待處理事項」區塊（待審作業數、待處理加入申請數）
- 統一術語：「任務」取代「作業」、「通過」取代「確認」
- 新增首次登入引導流程（Welcome message + 快速開始指引）

## Non-Goals

- **即時推送通知系統**（WebSocket / SSE）：本次僅在 Dashboard 實作伺服器端渲染的待處理計數，不建立即時推送基礎設施
- **Badge 圖示替換為 SVG**：需要設計完整圖示庫，規模過大，另開 change 處理
- **批量審閱功能**（勾選多份 → 批量通過）：互動設計複雜，另開 change 處理
- **PWA / Service Worker**：屬進階離線支援，不在本次範圍
- **學習歷程資料視覺化**（圖表）：需引入圖表庫，另開 change 處理

## Capabilities

### New Capabilities

- `a11y-foundation`: 全站無障礙基礎建設 — prefers-reduced-motion、skip-to-content、ARIA landmarks、色彩以外的狀態指示、鍵盤導航
- `shared-modal`: 共用模態元件 — ARIA dialog 語意、focus trap、ESC 關閉、行動端 bottom sheet、焦點還原
- `shared-toast`: 全站 Toast 通知系統 — success/error/info 變體、aria-live、自動消失、可堆疊
- `async-feedback`: 非同步操作回饋機制 — 按鈕 loading state、表單 submit 防重複、確認對話框
- `mobile-navigation`: 行動端導航重構 — 教師底部導航列、學生導航修復、平板 overflow 處理
- `form-validation`: 前端表單即時驗證 — 密碼強度、日期範圍、邀請碼格式、username 唯一性
- `empty-states`: 統一空狀態元件 — 依角色顯示引導、Dashboard 待處理事項、首次登入引導
- `design-tokens`: 設計系統統一 — 按鈕語意、card padding、content max-width、body text size、色彩一致性
- `tailwind-build`: Tailwind CSS 建構管線 — 替換 Play CDN、生成靜態 CSS、效能優化

### Modified Capabilities

（無現有 spec 需要修改）

## Impact

- **受影響模板**：全部 27 個 HTML 模板（`src/templates/**/*.html`）
- **核心檔案**：`src/templates/shared/base.html`（全站 layout、sidebar、bottom nav、全域 JS）
- **建構工具**：新增 Tailwind CLI 設定（`tailwind.config.js`、`package.json` 或對應設定）
- **靜態資源**：新增產出的 CSS 檔案（`src/static/css/`）
- **不影響後端邏輯**：所有變更限於前端模板與靜態資源，不觸及 Python router/service/model 層
- **例外**：Dashboard 待處理事項需要在 `src/pages/router.py` 的 dashboard view 增加查詢邏輯
