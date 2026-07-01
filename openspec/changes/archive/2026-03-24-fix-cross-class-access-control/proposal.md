## Problem

系統存在多處跨班級授權漏洞（IDOR / CWE-639 / CWE-863），任何擁有 `MANAGE_TASKS` 權限的教師可操作不屬於自己管理的班級資源：

1. **任務模板跨班級操作（CRITICAL）**：`PATCH/DELETE /templates/{template_id}` 及 `POST /classes/{class_id}/templates`、schedule-rules、template-assignments 僅檢查 `MANAGE_TASKS` 全域權限，未驗證教師是否屬於該班級。
2. **提交審查跨班級操作（CRITICAL）**：`POST /api/submissions/{id}/approve`、`reject`、`comment` 僅檢查 `MANAGE_TASKS`，未驗證該提交所屬班級。
3. **動態貼文跨班級刪除（CRITICAL）**：`DELETE /posts/{post_id}` 對教師僅檢查全域 `MANAGE_CLASS` 旗標。
4. **積分跨班級操作（CRITICAL）**：`POST /api/points/deduct`、`/point-revoke`、`PATCH /point-config` 僅檢查 `MANAGE_TASKS`，可操作任意班級學生積分。
5. **徽章跨班級操作（CRITICAL）**：`POST /classes/{class_id}/badges` 及 award 端點僅檢查 `MANAGE_TASKS`。
6. **獎品跨班級操作（CRITICAL）**：prizes CRUD 端點僅檢查 `MANAGE_TASKS`。
7. **出席修正跨班級操作（HIGH）**：`POST /api/classes/{class_id}/attendance/correct` 使用全域 `require_permission(MANAGE_CLASS)` 而非 `can_manage_class(user, cls)`。
8. **排行榜/今日模板資訊洩漏（MEDIUM）**：`GET /classes/{class_id}/leaderboard` 和 `GET /classes/{class_id}/today-template` 未驗證班級成員身分。

## Root Cause

這些端點使用 `require_permission(MANAGE_TASKS)` 或直接檢查 `user.permissions & MANAGE_CLASS`，這是「全域」權限檢查。缺少第二層「班級範圍」授權驗證（即 `can_manage_class(user, cls)` 呼叫），導致有該權限的教師可操作任意班級的資源。

## Proposed Solution

為所有受影響端點加入班級範圍授權檢查：
- 從資源物件或 URL 參數取得 `class_id`
- 載入 Class 文件
- 呼叫 `can_manage_class(user, cls)` 驗證
- 驗證失敗回傳 HTTP 403
- 對唯讀資訊端點（leaderboard、today-template）加入班級成員身分驗證

## Success Criteria

- 教師 A 管理班級 Alpha，教師 B 管理班級 Beta
- 教師 A 無法修改/刪除班級 Beta 的模板 → 403
- 教師 A 無法審查/退回班級 Beta 的提交 → 403
- 教師 A 無法刪除班級 Beta 的動態貼文 → 403
- 教師 A 無法操作班級 Beta 的積分、徽章、獎品 → 403
- 教師 A 無法修正班級 Beta 的出席紀錄 → 403
- 非班級成員無法查看排行榜或今日模板 → 403
- 有 `MANAGE_ALL_CLASSES` 權限的管理員不受影響

## Impact

- 受影響的 Spec：`task-templates`、`submission-approval`、`community-feed`、`points-system`、`badge-system`、`checkin`、`leaderboard`
- 受影響的程式碼：
  - `src/tasks/templates/router.py`（create, schedule, assign, update, delete, archive, unarchive）
  - `src/tasks/submissions/router.py`（approve, reject, comment）
  - `src/community/feed/router.py`（delete post）
  - `src/gamification/points/router.py`（deduct, revoke, config）
  - `src/gamification/badges/router.py`（create, award）
  - `src/gamification/prizes/router.py`（create, update, delete）
  - `src/tasks/checkin/router.py`（attendance correct）
  - `src/gamification/leaderboard/router.py`（class leaderboard）
