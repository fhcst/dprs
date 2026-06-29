## 1. 呼叫端靜態性複驗（前置）

- [x] 1.1 複驗 `empty_state` 全部 6 個呼叫端的 `icon` 實參皆為模板內寫死的靜態 SVG 字面值、無變數插值、無使用者輸入，以建立「icon 參數限定可信任靜態 markup」決策的事實基礎：逐一檢視 `src/templates/student/dashboard.html:263`、`:363`、`src/templates/student/learning_history.html:125`、`src/templates/student/badges.html:66`、`src/templates/student/class_history.html:116`、`src/templates/community/feed.html:82`。驗證：以 `grep -n "empty_state(" -A2 src/templates` 人工審視，確認每處 `icon=` 後緊接 `'<svg ...>'` 靜態字串字面值，無任何使用者可控變數，審視結論為「6 處皆靜態」。

## 2. 實作修正

- [x] 2.1 套用「採用方案 A 最小修改 icon 輸出為 safe」：將 `src/templates/shared/macros.html` 第 20 行 `{{ icon }}` 改為 `{{ icon | safe }}`，使「Unified empty state component」macro 把傳入的靜態 SVG 以 HTML 渲染（圖示）而非被 autoescape 跳脫為原始碼文字。驗證：`grep -n "icon | safe" src/templates/shared/macros.html` 命中第 20 行；於瀏覽器檢視任一空狀態（如學生 dashboard「尚未加入任何班級」）確認顯示 SVG 圖示而非 `<svg ...>` 文字。
- [x] 2.2 落實「icon 參數限定可信任靜態 markup」契約：在 `src/templates/shared/macros.html` 的 `empty_state` macro 加入 inline 註解，明確限定 `icon` 僅接受可信任靜態 markup（如模板寫死的 SVG 字面值）、嚴禁傳入使用者可控資料（否則造成 XSS），並說明 `title`/`description`/`cta_text`/`cta_href` 維持 autoescape、不套 `| safe`。驗證：開啟 `macros.html` 確認 `icon` 上方／macro 標頭含此限制註解，且僅 `icon` 一處使用 `| safe`。
- [x] [P] 2.3 套用「於 security-notes.md 登記 safe 靜態例外」：在 `docs/security-notes.md` 新增一行紀錄——`empty_state` macro 的 `icon` 採 `| safe` 僅限靜態 SVG 例外，與 SEC-WATCH-001（不對使用者輸入用 `| safe`）並存不衝突，留下可追溯決策軌跡。驗證：`grep -n "empty_state" docs/security-notes.md` 命中該新增紀錄行。

## 3. 驗收

- [x] 3.1 全站驗收「Unified empty state component」修復成效：6 處空狀態（dashboard 兩處、learning_history、badges、class_history、feed）皆渲染為 SVG 圖示、畫面無原始碼文字，且未對任何使用者可控資料套用 `| safe`。驗證：`grep -rn "| safe" src/templates | wc -l` 結果為 `1`（僅 `macros.html` 一處）；人工逐頁檢視 6 處空狀態確認圖示正確顯示。
