## 1. 後端 API

- [x] [P] 1.1 在 `src/core/classes/service.py` 新增 `list_students_for_invite(class_id, offset=0, limit=100)` 函式：查詢所有 `IdentityTag.STUDENT` 使用者，排除已為 `class_id` 成員的使用者，按 `class_name` ASC → `seat_number` ASC 排序，回傳 `(students, total)` tuple，每個 student 包含 `user_id`、`display_name`、`name`、`class_name`、`seat_number`、`tags`（Paginated student enumeration API）
- [x] [P] 1.2 在 `src/core/classes/router.py` 新增 `GET /classes/{class_id}/invite/students` 端點：接受 `offset`（預設 0）和 `limit`（預設 100）查詢參數，呼叫 `list_students_for_invite()`，回傳 `{"students": [...], "total": N, "offset": M, "limit": L}` 格式，需要 `can_manage_class` 授權檢查（分頁 API 設計）

## 2. 前端重寫

- [x] 2.1 重寫 `src/templates/teacher/class_members.html` 的批次邀請區塊：移除舊的搜尋輸入和搜尋結果區域，改為新的 UI 結構——頂部分組切換（按班級/按標籤 radio buttons）+ 搜尋過濾輸入框，中間為可摺疊分組面板區域，底部為已選取計數 + 全選 checkbox + 加入按鈕（Teacher batch-invites students to a class）
- [x] 2.2 實作 JavaScript lazy loading 策略：頁面載入時呼叫 `GET /classes/{class_id}/invite/students?offset=0&limit=100`，取得首批資料後自動連續載入剩餘分頁（offset += limit 直到 offset >= total），在載入期間顯示進度指示器（如「載入中 100/250」），所有資料存入全域 `allStudents` 陣列（Lazy loading with automatic continuation）
- [x] 2.3 實作按班級分組渲染函式（Grade-level grouping by class_name prefix）：從 `allStudents` 中提取 `class_name` 首碼作為年級分組鍵，第二層按 `class_name` 全名分組，組內按 `seat_number` 排序，`class_name` 為空的學生歸入「未分類」組，每個組渲染為可摺疊面板（`<details>` 元素），組標題包含學生數量和「全選」checkbox
- [x] 2.4 實作按標籤分組渲染函式（Tag-based grouping mode）：遍歷每個學生的 `tags` 陣列，將學生放入對應標籤組（一人可出現多組），`tags` 為空的學生歸入「無標籤」組，渲染結構與班級分組一致
- [x] 2.5 實作分組與切換機制：radio button 切換時呼叫對應的渲染函式重新渲染面板區域，切換時保留已選取狀態（選取狀態管理 — 使用 `Set<user_id>` 儲存）
- [x] 2.6 實作分類全選行為（Category select-all）：每個組的「全選」checkbox 勾選時選取該組所有可見學生，取消時取消全部，部分選取時顯示 indeterminate 狀態（`checkbox.indeterminate = true`），學生個別 checkbox 變更時更新所屬組的全選狀態，底部全域「全選」作用於所有可見學生
- [x] 2.7 實作 client-side 搜尋過濾（Client-side search filter）：搜尋輸入框 `oninput` 事件觸發時，若資料未全部載入則先完成載入（搜尋過濾觸發全量載入），然後對 `allStudents` 做 case-insensitive substring match（匹配 `name`、`display_name`、`class_name`、`seat_number` 字串、`tags` 各值），將不匹配的學生隱藏，空的分組自動隱藏，清空搜尋時恢復全部顯示
- [x] 2.8 實作按標籤分組時的跨組選取同步：當學生在一個標籤組被勾選/取消時，同一學生在其他標籤組中的 checkbox 也同步更新狀態（因為 `Set<user_id>` 是單一來源，需要在 DOM 上反映）

## 3. 測試

- [x] [P] 3.1 在 `tests/` 新增 `test_invite_enumerate.py`：測試 `list_students_for_invite()` 函式——正確排除已加入成員、按 class_name + seat_number 排序、offset/limit 分頁正確、offset 超出 total 時回傳空陣列
- [x] [P] 3.2 在 `tests/` 新增 `test_invite_enumerate.py`（同檔）：測試 `GET /classes/{class_id}/invite/students` 端點——回傳格式包含 students/total/offset/limit、未授權時回傳 403、回傳資料包含 tags 欄位
