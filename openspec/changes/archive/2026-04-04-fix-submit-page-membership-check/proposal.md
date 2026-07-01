## Why

### Problem

學生版 `GET /pages/student/classes/{class_id}/submit` 目前只要求登入，卻會在未驗證班級成員身分的情況下直接載入當日任務模板與退件重交資訊。這讓非班級成員只要知道 `class_id` 就能窺視私有班級的作業頁內容。

### Root Cause

同一個提交流程的瀏覽頁與寫入頁沒有使用一致的授權條件。`POST /classes/{class_id}/submit` 會檢查 `ClassMembership`，但對應的 SSR submit page 沒有在讀取模板前先驗證成員資格。

## What Changes

- 在學生 submit page 載入任務模板、退件狀態與錯誤訊息前，先驗證目前使用者是否屬於該班級。
- 將非成員存取 submit page 的結果固定為 HTTP 403，避免頁面先暴露「今日無任務模板」或其他班級內部資訊。
- 補上 submit page 的回歸測試，覆蓋班級成員可進入、非成員被拒絕兩條路徑。

## Non-Goals

- 不處理教師端跨班級授權問題；那些 route 需要獨立 change 整理。
- 不變更提交表單 `POST /classes/{class_id}/submit` 的既有商業規則。
- 不重新設計 class-scoped authorization helper，只修正這個學生頁面的缺漏。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `task-submissions`: 學生 submit page 在顯示當日模板前必須驗證使用者為該班級成員，非成員不得看到模板或退件資訊。

## Impact

- Affected specs: `task-submissions`
- Affected code: `src/tasks/submissions/router.py`
- Affected tests: `tests/test_pages.py`, `tests/test_dashboard_and_page_bugs.py`
