## Context

目前「成員管理」頁面的批次邀請學生區塊（`class_members.html`）採用搜尋優先模式：學生清單為空，教師輸入關鍵字後透過 `GET /classes/{class_id}/invite/search?q=...` 取得符合條件的學生。後端 `search_students_for_invite()` 每次呼叫都會載入所有 `IdentityTag.STUDENT` 使用者並在記憶體中過濾。

學生資料模型已包含分類所需欄位：
- `User.student_profile.class_name`（行政班級，如 "301班"，首碼為年級）
- `User.student_profile.seat_number`（座號）
- `User.tags: list[str]`（多用途標籤，已存在但未被邀請流程使用）

## Goals / Non-Goals

**Goals:**

- 頁面載入時即列出所有可邀請學生，按分類分組顯示
- 支援雙層分組（年級 → 行政班級）和替代分組（按標籤）
- 每個分組提供「全選」功能
- 搜尋欄作為即時過濾器，client-side 全欄位匹配
- API 支援分頁以控制初始載入量

**Non-Goals:**

- Server-side 搜尋 + WebSocket（方案 A）— future work
- 科系欄位分類 — 待技術高中需求確認
- 移除舊搜尋端點 — 保留向後相容

## Decisions

### 分頁 API 設計

新增 `GET /classes/{class_id}/invite/students?offset=0&limit=100` 端點。

回傳格式：
```json
{
  "students": [
    {
      "user_id": "...",
      "display_name": "王小明",
      "name": "王小明",
      "class_name": "301班",
      "seat_number": 1,
      "tags": ["社團A", "資優班"]
    }
  ],
  "total": 250,
  "offset": 0,
  "limit": 100
}
```

**為什麼不用 cursor-based pagination**：學生清單是靜態的（邀請操作期間不會頻繁變動），offset-based 更簡單且前端需要知道 `total` 來顯示進度。排序固定為 `class_name` ASC → `seat_number` ASC，保證分頁穩定。

### Lazy loading 策略

前端在頁面載入時發第一次請求（`offset=0, limit=100`），渲染首批學生。之後自動連續載入剩餘分頁（不等滾動觸發），直到 `offset >= total`。

**為什麼不用 infinite scroll**：教師需要看到完整的分類結構和學生總數來做決策，連續載入讓資料儘快完整，而非依賴滾動行為。

### 搜尋過濾觸發全量載入

當教師在搜尋欄輸入文字時：
1. 若資料尚未全部載入，立即發請求載完剩餘分頁
2. 載入完成後，在前端做 client-side 過濾（姓名、班級、座號、tags 全欄位匹配）
3. 過濾後空的分組自動隱藏
4. 清空搜尋欄時恢復全部顯示

### 分組與切換機制

前端維護完整的學生陣列，分組由 JavaScript 即時計算：

- **按班級模式（預設）**：從 `class_name` 首碼提取年級作為第一層，`class_name` 作為第二層
- **按標籤模式**：遍歷每個學生的 `tags` 陣列，將學生放入對應的標籤組（一個學生可出現在多組）
- **未分類 / 無標籤**：`class_name` 為空的學生歸入「未分類」；`tags` 為空的學生歸入「無標籤」

切換分組時不需重新載入資料，僅重新渲染 DOM。

### 分類全選行為

每個分組標題旁的「全選」checkbox 行為：
- 勾選時，選取該分組下**所有當前可見**（未被搜尋過濾隱藏的）學生
- 取消時，取消該分組下所有學生的選取
- 若分組內有部分學生被手動選取，checkbox 顯示為 indeterminate 狀態
- 底部的全域「全選」作用於所有可見學生

### 選取狀態管理

使用 JavaScript `Set` 儲存已選取的 `user_id`。切換分組模式時，選取狀態保留（因為是以 `user_id` 為鍵，不受分組方式影響）。底部顯示「已選取 N 人」計數器。

## Risks / Trade-offs

- **[學生總數過大]** → 學校場景預期數百到數千人，全量載入可接受。若超過預期，搜尋觸發全量載入可能有短暫延遲（1-2 秒）。未來可切換為方案 A（server-side + WebSocket）。
- **[按標籤分組時學生重複出現]** → 一個學生可出現在多個標籤組中，教師可能重複選取。由於選取狀態用 `Set<user_id>` 管理，實際加入時不會重複，但視覺上需要同步 — 當學生在一個組被勾選時，其他組中的同一學生也應同步顯示為已勾選。
- **[分頁期間新學生加入]** → offset-based 分頁在分批載入期間若有新學生被管理者建立，可能導致重複或遺漏。風險低（邀請操作通常不與建立帳號同時進行）。

## Open Questions

（無 — 所有設計問題已在討論中解決）
