# 安全審計備查紀錄

本文件記錄安全審計中發現的已知問題、設計決策、與需持續注意的潛在風險。
供開發時備查，避免引入或加劇已知風險。

**最後更新**：2026-04-04（新增 badge detail / revoke 端點安全設計）

---

## 已修復漏洞

### IDOR-001：手動頒發 badge 未驗證學生成員身分

- **嚴重度**：Medium
- **位置**：`src/gamification/badges/router.py` — `manual_award_badge`
- **端點**：`POST /classes/{class_id}/badges/{badge_id}/award`
- **問題**：`student_id` 來自 request body，但未驗證該使用者是否為該班級的學生成員。
- **修復**：在 `award_badge()` 呼叫前查詢 `ClassMembership`，確認 `student_id` 在 `class_id` 中具有 `role == "student"`，否則回傳 HTTP 403。
- **測試**：`tests/test_badges.py` — 3 個測試覆蓋正常路徑、非成員、非學生角色
- **追蹤**：Spectra change `fix-badge-award-idor`
- **狀態**：✅ 已修復（2026-04-04）

---

## 設計決策（已知且接受）

### SEC-DESIGN-001：CSRF middleware 豁免 JSON API

- **位置**：`src/shared/csrf.py`
- **決策**：`CSRFMiddleware` 僅保護 `application/x-www-form-urlencoded` 和 `multipart/form-data`，JSON API 被豁免。
- **風險評估**：Low
- **為什麼可以接受**：
  - `application/json` 是 non-simple content type，會觸發 CORS preflight
  - Cookie 設定 `SameSite=Lax`，瀏覽器不會在跨站 POST 中帶 cookie
  - 兩層防護同時失效的機率極低
- **注意事項**：若未來變更 cookie 的 `SameSite` 設定或 CORS 政策，需重新評估此決策。

### SEC-DESIGN-002：`empty_state` macro 的 `icon` 採 `| safe`（僅限靜態 SVG 例外）

- **位置**：`src/templates/shared/macros.html` — `empty_state` macro 的 `icon` 輸出
- **決策**：`icon` 以 `{{ icon | safe }}` 原樣渲染（繞過 autoescape），**僅限**全部 6 個呼叫端傳入的模板內寫死靜態 SVG 字面值；`title`/`description`/`cta_text`/`cta_href` 維持 autoescape、不套 `| safe`。此為專案唯一一處 `| safe`，與 SEC-WATCH-001（永遠不要對使用者輸入用 `| safe`）並存且不衝突——本例不接受任何使用者輸入；嚴禁將此模式推廣至使用者可控資料。

---

## 潛在風險（需持續監控）

### SEC-WATCH-001：Markdown 描述的 XSS 隱患

- **位置**：
  - `src/templates/student/badges.html:38` — `{{ defn.description }}`
  - `src/templates/teacher/badges_manage.html:176` — `{{ b.description[:80] }}`
- **目前狀態**：**安全** — Jinja2 auto-escape 開啟，HTML 標籤會被轉義
- **風險情境**：若未來改為 `{{ defn.description | safe }}` 或在前端用 JavaScript 進行 Markdown → HTML 渲染（例如 `innerHTML = marked(description)`），將直接導致 Stored XSS
- **建議**：
  - 永遠不要對使用者輸入的內容使用 `| safe` filter
  - 若需要前端 Markdown 渲染，必須使用 sanitizer（如 DOMPurify）
  - Badge description 在 Milkdown 編輯器中是安全的（ProseMirror sanitized DOM），但儲存後在其他頁面渲染時需注意

### SEC-WATCH-002：`class_student_stats` 的 `windows` 參數無上界

- **位置**：`src/gamification/badges/router.py:191-274` — `class_student_stats`
- **端點**：`GET /classes/{class_id}/students/stats?windows=7,30`
- **問題**：`windows` 查詢參數沒有限制：
  - 天數值無上界（例如 `windows=999999999` 會產生極大時間範圍查詢）
  - 窗口數量無上限（例如 `windows=1,2,3,4,...,1000` 會對每個學生做 2000 次額外查詢）
- **風險評估**：Low — 端點需要 `MANAGE_OWN_CLASS` 權限，只有教師可存取
- **建議**：考慮限制 `window_days` 最多 5 個窗口、每個窗口最大 365 天

### SEC-WATCH-003：`deleteBadge` onclick 中的引號處理

- **位置**：`src/templates/teacher/badges_manage.html:190`
- **程式碼**：`onclick="deleteBadge('{{ b.id }}', '{{ b.name }}')"`
- **目前狀態**：**安全** — Jinja2 auto-escape 將 `'` 轉為 `&#39;`，`"` 轉為 `&quot;`
- **風險情境**：此模式較脆弱。若未來有人將 auto-escape 關閉（`{% autoescape false %}`）或在其他未啟用 auto-escape 的模板引擎中複製此模式，會導致 XSS
- **建議**：考慮改用 `data-*` 屬性 + JavaScript event delegation 取代 inline onclick，更為穩固

---

## Badge Detail 與 Revoke 端點安全設計（2026-04-04 新增）

### GET /classes/{class_id}/badges/{badge_id}/detail

- **端點**：`src/gamification/badges/router.py` — `badge_detail`
- **IDOR 防護**：三重驗證
  1. `can_manage_class(teacher, cls)` — 教師必須管理此班級
  2. `badge.class_id == class_id` — 徽章必須屬於此班級
  3. 學生清單來自 `ClassMembership(class_id, role="student")`，不接受外部 student_id 參數
- **只回傳 active awards**：使用 `active_awards_query`，已撤銷 award (`revoked_at != None`) 不出現在 awarded 清單
- **權限**：`require_permission(MANAGE_TASKS)`

### POST /classes/{class_id}/badges/{badge_id}/revoke

- **端點**：`src/gamification/badges/router.py` — `revoke_badge_award`
- **IDOR 防護**：四重驗證
  1. `can_manage_class(teacher, cls)` — 教師必須管理此班級
  2. `badge.class_id == class_id` — 徽章必須屬於此班級
  3. `award.badge_id == badge_id` + `award.class_id == class_id` — award 必須屬於此徽章和班級（防止跨班或跨徽章操作）
  4. `award.revoked_at is None` — 防止重複撤銷（回傳 HTTP 409）
- **Soft delete**：設定 `revoked_at` + `revoked_by`，保留審計軌跡
- **權限**：`require_permission(MANAGE_TASKS)`

### 前端 XSS 防護（detail modal）

- `renderDetailModal` 中的所有使用者輸入（`student_name`, `award_id`, `student_id`）均透過 `escHtml()` 和 `escAttr()` 轉義後再插入 DOM
- 不使用 `innerHTML` 直接插入未轉義內容
- `onclick` 中的動態值透過 `escAttr()` 轉義，防止屬性注入

---

## 已通過的檢查項目

以下項目在審計中確認為安全：

| 檢查項目 | 狀態 | 說明 |
|---------|------|------|
| Badge CRUD IDOR | ✅ 安全 | 所有 endpoint 檢查 `can_manage_class` + `badge.class_id == class_id` |
| Badge 管理頁面授權 | ✅ 安全 | `badges_manage_page` 有 `can_manage_class` 檢查 |
| API 認證 | ✅ 安全 | 使用 `require_permission(MANAGE_TASKS)` |
| Trigger 互斥驗證 | ✅ 安全 | `model_validator` 防止同時設定 `trigger_key` 和 `trigger_rule_id` |
| 已頒發 badge 刪除保護 | ✅ 安全 | `award_count > 0` 時禁止刪除（使用 `active_awards_query` 排除已撤銷） |
| Template injection | ✅ 安全 | Jinja2 auto-escape 開啟 |
| `tojson` filter | ✅ 安全 | Jinja2 `tojson` 正確 escape HTML entities |
| 重複頒發防護 | ✅ 安全 | `award_badge()` 只查 active award 防重複 |
| Detail API IDOR | ✅ 安全 | 三重驗證（see above） |
| Revoke API IDOR | ✅ 安全 | 四重驗證（see above） |
| Detail modal XSS | ✅ 安全 | `escHtml` + `escAttr` 轉義所有動態內容 |
