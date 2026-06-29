## Context

`empty_state` 是專案目前唯一的共用 Jinja2 macro（`src/templates/shared/macros.html:16`），用於全站空狀態卡片。它以 `{{ icon }}`（`:20`）輸出圖示參數。

渲染環境為 fastapi-webpage 內部建立的 Jinja2 environment（`src/shared/webpage.py` 的 `WebPage` 單例），autoescape 為開啟——已於執行期實測：載入 `shared.webpage.webpage._template.env`，`env.autoescape == True`（static True）。專案未覆寫此設定，也未使用 Starlette `Jinja2Templates`。

因此 macro 傳入的 SVG 字串被 autoescape 跳脫成 `&lt;svg&gt;...` 文字，呈現為原始碼而非圖示。全部 6 個呼叫端傳入的 `icon` 皆為模板內寫死的靜態 SVG 字面值（已逐一查核，見 Implementation Contract）。

值得注意的安全前提：目前 `src/templates/` 全域 `| safe` 數量為 0，且 `docs/security-notes.md`（SEC-WATCH-001）明訂守則「永遠不要對使用者輸入使用 `| safe`」。本次修法會引入專案第一個 `| safe`，必須謹慎並留下紀錄。

## Goals / Non-Goals

**Goals:**

- 讓 6 處空狀態正確顯示 SVG 圖示，消除原始碼文字。
- 以最小改動修正，且不對任何使用者可控資料套用 `| safe`。
- 明確記錄「靜態 SVG `| safe` 例外」，避免日後被誤用為通用模式。

**Non-Goals:**

- **方案 B（named-icon / `{% call %}` block / include 片段重構）**：較乾淨且不引入 `| safe` 先例，但需改動 macro 介面與全部 6 個呼叫端，改動面大；本次已由產品決策拍板採方案 A，故不實作。
- 不調整 Jinja2 autoescape 全域設定。
- 不更動 `icon` 以外的 macro 參數（`title`、`description`、`cta_text`、`cta_href` 維持 autoescape 跳脫）。
- 不新增前端 sanitizer（DOMPurify）——本案無使用者輸入流入 `icon`，不需要。

## Decisions

### 採用方案 A 最小修改 icon 輸出為 safe

把 `src/templates/shared/macros.html` 的 `{{ icon }}` 改為 `{{ icon | safe }}`。`| safe` 標記字串為已信任，繞過 autoescape，使 SVG 以 HTML 渲染。

**為什麼選 A 而非 B**：A 為一行修改、零呼叫端改動、風險最低；B 雖避免 `| safe` 先例但需重構 macro 介面與 6 個呼叫端。`icon` 的全部呼叫端皆為靜態 SVG 字面值、無使用者輸入路徑，A 的安全風險可被「呼叫端契約 + 文件註解 + 安全守則紀錄」完整框限，故採 A。

### icon 參數限定可信任靜態 markup

在 `empty_state` macro 加上 doc 註解，明確限定 `icon` 參數**只接受可信任的靜態 markup（如模板寫死的 SVG 字面值）**，**嚴禁傳入使用者可控資料**（會造成 XSS）。`title` / `description` / `cta_text` / `cta_href` 不套用 `| safe`，維持 autoescape 防護。此契約讓「為何此 `| safe` 安全」對未來維護者一目了然，並界定唯一安全用法。

### 於 security-notes.md 登記 safe 靜態例外

在 `docs/security-notes.md` 新增一行紀錄此例外：`empty_state` macro 的 `icon` 採 `| safe` 僅限靜態 SVG，與既有 SEC-WATCH-001 守則（不對使用者輸入用 `| safe`）並存且不衝突。目的是留下可追溯的決策軌跡，避免他人把此模式誤推廣到使用者輸入欄位。

## Implementation Contract

**Behavior**：修法後，6 處空狀態卡片皆渲染為實際 SVG 圖示，畫面上不再出現 `<svg ...>` 原始碼文字。其餘 macro 文字參數（`title`、`description`、`cta_text`、`cta_href`）行為不變，仍受 autoescape 跳脫保護。

**Interface / data shape**：`empty_state(icon, title, description, cta_text, cta_href)` 簽章不變。唯一語意變更為 `icon` 改以 raw HTML 渲染，並新增契約：`icon` 只能是可信任靜態 markup。

**呼叫端複驗（驗收前置，不需改動）**：須確認以下 6 處 `icon=` 實參皆為模板內靜態 SVG 字面值、無變數插值、無使用者資料：
- `src/templates/student/dashboard.html:263`（學業帽 SVG）、`:363`（使用者群組 SVG）
- `src/templates/student/learning_history.html:125`（書本 SVG）
- `src/templates/student/badges.html:66`（獎盃 SVG）
- `src/templates/student/class_history.html:116`（書本 SVG）
- `src/templates/community/feed.html:82`（對話框 SVG）

**Failure modes**：若未來有呼叫端把使用者可控字串傳入 `icon`，將造成 Stored/Reflected XSS——此風險由 macro doc 註解與 security-notes 紀錄明文警示，屬人為違規而非預期失敗路徑。

**Acceptance criteria**：
- `src/templates/shared/macros.html` 第 20 行為 `{{ icon | safe }}`，且 macro 含 `icon` 限定靜態 markup 的 doc 註解。
- `src/templates/` 全域 `| safe` 計數恰為 1，且該唯一一處即此 macro。
- `docs/security-notes.md` 含一行靜態 SVG `| safe` 例外紀錄。
- 6 處空狀態手動檢視顯示圖示而非原始碼文字。

**Scope boundaries**：僅改 `empty_state` macro 的 `icon` 輸出與其 doc 註解，加上 `docs/security-notes.md` 一行紀錄。不改任何呼叫端模板、不改 autoescape 設定、不引入第二個 `| safe`。

## Risks / Trade-offs

- [引入專案第一個 `| safe`，可能被誤用為通用模式] → macro doc 註解限定靜態 markup ＋ `docs/security-notes.md` 明文登記例外與限制；`title`/`description` 等文字參數維持不套 `| safe`。
- [未來呼叫端誤把使用者資料當 `icon`] → 契約已明文禁止；`empty_state` 目前為專案唯一 macro，呼叫面集中、可控。
- [方案 A 未根除 `| safe` 慣例疑慮] → 已評估方案 B 並由產品決策接受 A，差異與理由留存於本文件供日後重估。
