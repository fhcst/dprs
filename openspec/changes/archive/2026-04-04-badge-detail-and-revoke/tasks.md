## 1. Model 層：Badge award soft delete with revoke（soft delete 欄位設計）

- [x] 1.1 在 `src/gamification/badges/models.py` 的 `BadgeAward` class 新增 `revoked_at: Optional[datetime] = None` 和 `revoked_by: Optional[str] = None` 欄位（badge award soft delete with revoke）
- [x] 1.2 在 `src/gamification/badges/service.py` 新增 `active_awards_query(*filters)` helper function，預設附加 `BadgeAward.revoked_at == None` 過濾條件
- [x] 1.3 修改 `src/gamification/badges/service.py` 的 `award_badge()`，查重複 award 時使用 `active_awards_query` 只查未撤銷的 award，實現重新頒發已撤銷的徽章（re-awarding a previously revoked badge）
- [x] 1.4 修改 `src/gamification/badges/service.py` 的 `get_student_badges()`，只回傳未撤銷的 award（student views earned badges 排除 revoked）
- [x] 1.5 新增 `src/gamification/badges/service.py` 的 `revoke_badge(award_id, badge_id, class_id, revoked_by)` function，執行 soft delete（設定 revoked_at/revoked_by），回傳 award 或 None（teacher revokes badge award）

## 2. 既有查詢層面的 soft delete 過濾修正

- [x] [P] 2.1 修改 `src/gamification/badges/router.py` 的 `badges_manage_page` 中 `award_count` 查詢，使用 `active_awards_query` 排除已撤銷 award（revoked award is excluded from counts）
- [x] [P] 2.2 修改 `src/gamification/badges/router.py` 的 `delete_badge` 中 `award_count` 查詢，使用 `active_awards_query`（revoked award is excluded from counts）
- [x] [P] 2.3 修改 `src/gamification/badges/router.py` 的 `class_student_stats` 中 `badge_count` 查詢，使用 `active_awards_query`（revoked award is excluded from counts）
- [x] [P] 2.4 修改 `src/pages/router.py` 的 `dashboard_page` 中 `badge_count` 和 `badge_awards` 查詢，使用 `active_awards_query`（revoked award is excluded from counts）
- [x] [P] 2.5 修改 `src/gamification/badges/service.py` 的 `build_eval_context` 中 `badge_count` 查詢，使用 `active_awards_query`（revoked award is excluded from counts）
- [x] [P] 2.6 檢查 `src/gamification/leaderboard/router.py` 是否有 `BadgeAward` 查詢，若有則加上 soft delete 過濾（revoked award is excluded from counts）

## 3. 新增 API endpoint

- [x] 3.1 在 `src/gamification/badges/router.py` 新增 `GET /classes/{class_id}/badges/{badge_id}/detail` endpoint（detail API 設計），需驗證 `can_manage_class` 和 `badge.class_id == class_id`，回傳 badge metadata、`is_manual` flag、awarded 學生清單（含 award_id, student_name, awarded_at）、not_awarded 學生清單（從 ClassMembership 取得）
- [x] 3.2 在 `src/gamification/badges/router.py` 新增 `POST /classes/{class_id}/badges/{badge_id}/revoke` endpoint（revoke API 設計），需驗證 `can_manage_class`、`badge.class_id == class_id`、`award.badge_id == badge_id`、`award.class_id == class_id`、`award.revoked_at is None`，呼叫 `revoke_badge()` service

## 4. 前端 Modal UI 互動設計

- [x] 4.1 修改 `src/templates/teacher/badges_manage.html` 的徽章卡片，整行加上 `cursor-pointer` 和 click handler，點擊時 fetch detail API 並顯示 modal（badge detail modal displays awarded and not-awarded students）
- [x] 4.2 實作 modal 中「已獲得」區塊，顯示 student_name、awarded_at、「收回」按鈕；點擊「收回」呼叫 revoke API 並 in-place 更新 modal（badge revoke from detail modal）
- [x] 4.3 實作 modal 中「未獲得」區塊，手動徽章顯示「頒發」按鈕、自動觸發徽章隱藏按鈕；點擊「頒發」呼叫現有 award API 並 in-place 更新 modal（manual badge award from detail modal，award button hidden for automatic trigger badges）
- [x] 4.4 操作成功後同步更新徽章卡片上的「N 人獲得」數字
- [x] 4.5 將 `openBadgeDetail`、`closeBadgeDetail`、`closeBadgeDetailOnOverlay`、`awardFromDetail`、`revokeFromDetail` 改為 `window.xxx` 賦值，修正 `<script type="module">` 作用域限制導致 inline `onclick` 無法呼叫的問題（hotfix: ReferenceError in browser）

## 5. 安全與文件

- [x] 5.1 更新 `docs/security-notes.md`，記錄新增的 detail 和 revoke endpoint 安全設計（IDOR 防護 pattern、權限檢查）

## 6. 測試

- [x] [P] 6.1 在 `tests/test_badges.py` 新增 revoke 相關測試：正常收回、重複收回 (409)、跨班收回 (403/404)、非管理教師收回 (403)（teacher revokes badge award、non-managing teacher attempts to revoke、teacher attempts to revoke already-revoked award、teacher attempts to revoke award from another class）
- [x] [P] 6.2 在 `tests/test_badges.py` 新增 detail API 測試：正常查看、跨班查看 (403)、badge 不存在 (404)（badge detail API、teacher fetches badge detail for own class、teacher fetches badge detail for another class、badge not found or wrong class）
- [x] [P] 6.3 在 `tests/test_badges.py` 新增 re-award 測試：撤銷後重新頒發成功、未撤銷時重複頒發失敗 (409)（re-awarding a previously revoked badge、student with active award cannot receive duplicate）
- [x] [P] 6.4 在 `tests/test_badges.py` 新增 soft delete 過濾測試：撤銷後 student badges 不顯示、badge_count 不計入（revoked badge not shown to student、revoked award is excluded from counts）
