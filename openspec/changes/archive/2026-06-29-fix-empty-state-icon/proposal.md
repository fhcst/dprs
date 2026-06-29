## Why

`empty_state` macro（`src/templates/shared/macros.html:16` 定義、`:20` 輸出）以 `{{ icon }}` 輸出圖示，但渲染環境（fastapi-webpage 內部建立的 Jinja2 environment）autoescape 為開啟（已於執行期實測 `env.autoescape == True`）。所有 6 個呼叫端傳入的都是 SVG 字串，於是 SVG 標記被跳脫成原始碼文字——全站每個空狀態卡片都印出 `<svg ...>...</svg>` 字樣，而非圖示（實測可見於學生 dashboard「尚未加入任何班級」空狀態）。這是 P1 全站視覺瑕疵，須修正。

## What Changes

- **Bug Fix**：`src/templates/shared/macros.html` 的 `empty_state` macro 把 `{{ icon }}` 改為 `{{ icon | safe }}`，讓傳入的靜態 SVG 標記以 HTML 渲染而非被跳脫。
- **引入專案第一個 `| safe`（受控例外）**：目前 `src/templates/` 共有 0 個 `| safe`。本次修法刻意引入首例，**僅因 `icon` 參數的全部 6 個呼叫端皆傳入模板內寫死的靜態 SVG 字串字面值，永不接受使用者輸入**。
- **macro 文件註解**：在 `empty_state` macro 加註，明確限定 `icon` 參數只接受「可信任的靜態 markup」，禁止傳入使用者可控資料。
- **安全守則同步**：於 `docs/security-notes.md` 新增一行紀錄，登記此「靜態 SVG `| safe` 例外」，與既有守則「永遠不要對使用者輸入使用 `| safe`」對齊，避免日後誤用為通用模式。
- **不採方案 B**：不改用 named-icon／`{% call %}` block／include 片段等重構手法（見 design.md 取捨說明）。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `empty-states`：「Unified empty state component」requirement 的 `icon` 渲染行為，從「被 autoescape 跳脫成文字」改為「以可信任靜態 markup 原樣渲染」，並新增「`icon` 僅限可信任靜態 SVG、不得為使用者輸入」的契約限制。

## Impact

- 受影響程式碼：
  - `src/templates/shared/macros.html`（`empty_state` macro：`{{ icon }}` → `{{ icon | safe }}` ＋ doc 註解）
- 已盤點並須複驗為靜態 SVG 的 6 個呼叫端（不需改動，僅供驗收確認）：
  - `src/templates/student/dashboard.html:263`、`:363`
  - `src/templates/student/learning_history.html:125`
  - `src/templates/student/badges.html:66`
  - `src/templates/student/class_history.html:116`
  - `src/templates/community/feed.html:82`
- 受影響文件：`docs/security-notes.md`（新增靜態 SVG `| safe` 例外紀錄）
- 受影響 specs：`empty-states`（macro icon 渲染行為與契約變更）
- 無 API、資料模型、相依套件變更。
