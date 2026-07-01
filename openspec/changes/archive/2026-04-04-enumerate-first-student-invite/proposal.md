## Why

教師在「成員管理」頁面批次邀請學生時，目前採用「搜尋優先」模式——學生清單為空白，必須先輸入關鍵字搜尋才能看到學生。對於需要從整個學校中挑選學生的教師來說，這種模式效率低落，因為教師必須記得學生姓名或班級名稱才能開始操作。改為「枚舉優先」模式，讓所有可邀請的學生一開始就列出，並支援按行政班級或標籤分類瀏覽、批次選取，可大幅提升操作效率。

## What Changes

- **枚舉優先的學生清單**：頁面載入時即透過分頁 lazy loading 載入所有未加入的學生，按分類分組顯示
- **雙層分組瀏覽（按班級）**：第一層為年級（`class_name` 首碼），第二層為行政班級（`class_name` 全名），組內按 `seat_number` 排序
- **替代分組（按標籤）**：教師可切換為以 `User.tags` 作為分組鍵瀏覽，一個學生可出現在多個標籤組中
- **分類全選（category select）**：每個分組提供「全選」checkbox，一鍵選取該分類下所有學生
- **即時過濾搜尋**：搜尋欄改為 client-side 即時過濾（姓名、班級、座號、tags 全欄位匹配），過濾後空的分組自動隱藏，「全選」只作用於當前可見學生
- **新分頁 API 端點**：`GET /classes/{class_id}/invite/students` 回傳所有未加入的學生清單，支援 `offset` + `limit` 分頁，包含 `class_name`、`seat_number`、`tags` 欄位

## Non-Goals

- **Server-side 搜尋（方案 A）**：大量資料時改用 server-side 搜尋 + WebSocket 推送結果，留作 future work
- **科系欄位**：技術高中可能需要科系分類，但目前系統僅供普通高中使用，暫不實作
- **修改 User model**：`tags: list[str]` 欄位已存在，不需要變更資料模型
- **移除舊搜尋端點**：`GET /classes/{class_id}/invite/search` 保留向後相容，不在此次移除

## Capabilities

### New Capabilities

- `student-invite-enumerate`：枚舉優先的學生邀請流程，包含分頁載入、分類分組、分類全選、即時過濾搜尋

### Modified Capabilities

- `class-management`：批次邀請學生的前端互動方式從搜尋優先改為枚舉優先

## Impact

- 受影響程式碼：
  - `src/core/classes/service.py`（新增枚舉學生函式）
  - `src/core/classes/router.py`（新增分頁列表端點）
  - `src/templates/teacher/class_members.html`（重寫批次邀請區塊 UI 與 JS）
- 受影響 API：
  - 新增 `GET /classes/{class_id}/invite/students`（分頁枚舉）
  - 現有 `POST /classes/{class_id}/invite/batch`（不變）
- 受影響 specs：`class-management`（邀請流程行為變更）、新增 `student-invite-enumerate`
