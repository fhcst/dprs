## 1. 修復 IDOR 漏洞

- [x] 1.1 在 `src/gamification/badges/router.py` 的 `manual_award_badge` handler 中，於呼叫 `award_badge()` 之前，新增 `ClassMembership` 查詢：驗證 `body.student_id` 在 `class_id` 中具有 `role == "student"` 的成員記錄，若不存在則回傳 HTTP 403（detail: "Student is not a member of this class"）（Teacher awards badge manually）

## 2. 測試

- [x] [P] 2.1 在 `tests/test_badges.py` 新增測試：教師對班級內學生成員手動頒發 badge 成功（正常路徑驗證）
- [x] [P] 2.2 在 `tests/test_badges.py` 新增測試：教師對非班級成員的使用者頒發 badge 時回傳 403
- [x] [P] 2.3 在 `tests/test_badges.py` 新增測試：教師對班級內 role 為 `"teacher"` 的成員頒發 badge 時回傳 403
