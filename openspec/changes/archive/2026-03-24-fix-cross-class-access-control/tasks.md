## 1. 模板端點加入班級範圍授權

- [x] 1.1 在 `src/tasks/templates/router.py` 的 `update_template_endpoint`、`delete_template_endpoint`、`archive_template_endpoint`、`unarchive_template_endpoint` 中加入 `can_manage_class` 驗證（template modification requires class management permission）
- [x] 1.2 在 `src/tasks/templates/router.py` 的 `create_template_endpoint`、`create_schedule_rule`、`assign_template` 中加入 `can_manage_class` 驗證（template creation requires class management permission）

## 2. 提交審查端點加入班級範圍授權

- [x] [P] 2.1 在 `src/tasks/submissions/router.py` 的 `approve_submission`、`reject_submission`、`add_submission_comment` 中從 submission 取得 class_id，加入 `can_manage_class` 驗證（teacher approves a task submission / teacher rejects a task submission 跨班級授權修復）

## 3. 動態貼文刪除加入班級範圍授權

- [x] [P] 3.1 在 `src/community/feed/router.py` 的 `delete_post` 中對非 owner 教師加入 `can_manage_class` 驗證（feed post deletion requires class management permission）

## 4. 積分端點加入班級範圍授權

- [x] [P] 4.1 在 `src/gamification/points/router.py` 的 `deduct_student_points`、`revoke_student_points`、`update_point_config` 中加入 `can_manage_class` 驗證（points operations require class management permission）

## 5. 徽章端點加入班級範圍授權

- [x] [P] 5.1 在 `src/gamification/badges/router.py` 的 `create_badge`、`manual_award_badge` 中加入 `can_manage_class` 驗證（badge operations require class management permission）

## 6. 獎品端點加入班級範圍授權

- [x] [P] 6.1 在 `src/gamification/prizes/router.py` 的 `create_prize`、`update_prize`、`delete_prize` 中加入 `can_manage_class` 驗證

## 7. 出席修正端點修復授權

- [x] [P] 7.1 在 `src/tasks/checkin/router.py` 的 `correct_attendance` 中將 `require_permission(MANAGE_CLASS)` 替換為 `_require_manage(class_id, teacher)` 模式（teacher corrects attendance 跨班級授權修復）

## 8. 排行榜與今日模板加入成員驗證

- [x] [P] 8.1 在 `src/gamification/leaderboard/router.py` 的 `class_leaderboard` 中加入班級成員身分驗證（class leaderboard requires membership）
- [x] [P] 8.2 在 `src/tasks/templates/router.py` 的 `today_template` 中加入班級成員身分驗證

## 9. 測試

- [x] [P] 9.1 撰寫測試驗證跨班級模板操作被拒絕（template modification requires class management permission）
- [x] [P] 9.2 撰寫測試驗證跨班級提交審查被拒絕（teacher approves/rejects a task submission in another class → 403）
- [x] [P] 9.3 撰寫測試驗證跨班級積分/徽章/獎品操作被拒絕（points/badge/prizes operations in another class → 403）
- [x] [P] 9.4 撰寫測試驗證跨班級貼文刪除與出席修正被拒絕（feed post deletion / teacher corrects attendance in another class → 403）
- [x] [P] 9.5 撰寫測試驗證非成員無法查看排行榜（class leaderboard requires membership → 403）
