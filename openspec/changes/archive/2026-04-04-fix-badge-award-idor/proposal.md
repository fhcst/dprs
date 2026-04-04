## Problem

`POST /classes/{class_id}/badges/{badge_id}/award` 端點（`manual_award_badge`）接受 request body 中的 `student_id`，但未驗證該學生是否為該班級的成員。教師可以將 badge 頒發給不在該班級中的任何使用者，包括其他班級的學生、其他教師、甚至不存在的使用者 ID。

## Root Cause

`manual_award_badge` handler（`src/gamification/badges/router.py:145-172`）僅檢查：
1. 教師是否有權管理該班級（`can_manage_class`）
2. Badge 是否屬於該班級（`badge.class_id != class_id`）

但缺少第三項檢查：`student_id` 是否為該班級的學生成員（`ClassMembership` 驗證）。

## Proposed Solution

在 `manual_award_badge` 中，於呼叫 `award_badge()` 之前，查詢 `ClassMembership` 確認 `student_id` 在該 `class_id` 中具有 `"student"` 角色。若不是，回傳 HTTP 403。

## Non-Goals

- 不修改自動觸發器（code triggers / DSL triggers）的授獎邏輯 — 這些由系統事件觸發，student_id 已經是事件的來源學生
- 不修改 `award_badge` service function 本身 — 驗證責任在 router 層

## Success Criteria

- 教師嘗試對非班級學生成員頒發 badge 時，收到 HTTP 403 錯誤
- 教師對班級內學生成員頒發 badge 時，行為不變
- 新增對應的測試案例

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `badge-system`：手動頒發 badge 時新增 student membership 驗證

## Impact

- 受影響程式碼：`src/gamification/badges/router.py`（`manual_award_badge` handler）
- 受影響 API：`POST /classes/{class_id}/badges/{badge_id}/award`
- 受影響測試：`tests/test_badges.py`
