## Why

徽章管理頁面目前只有建立、編輯、刪除功能，教師無法查看某個徽章的持有狀態（誰得到、誰沒得到），也無法手動頒發或收回徽章。後端的手動頒發 API (`POST .../award`) 已存在但前端沒有 UI，而收回（revoke）機制則完全不存在。教師需要完整的徽章生命週期管理能力。

## What Changes

- `BadgeAward` model 新增 `revoked_at`（datetime, nullable）和 `revoked_by`（str, nullable）欄位，支援 soft delete
- 新增 `GET /classes/{class_id}/badges/{badge_id}/detail` API，回傳該徽章的已獲得 / 未獲得學生清單
- 新增 `POST /classes/{class_id}/badges/{badge_id}/revoke` API，soft delete 指定 award（填入 revoked_at/revoked_by）
- 現有的 `award_badge` service 和相關查詢需排除已撤銷的 award（`revoked_at is None`）
- 徽章管理頁面：點擊徽章卡片開啟 detail modal，顯示兩組學生清單
  - 已獲得學生：顯示獲得時間，所有徽章皆可「收回」
  - 未獲得學生：手動徽章可直接「頒發」，自動觸發徽章不顯示頒發按鈕

## Non-Goals

- 獨立的徽章詳情頁面（future work，目前以 modal 實作）
- 學生搜尋、過濾、分頁功能（future work，目前學生數量不多）
- 審計日誌頁面（收回歷史的查看介面，future work）
- 批次頒發 / 批次收回

## Capabilities

### New Capabilities

- `badge-detail-modal`: 徽章詳情 modal 介面，教師點擊徽章卡片可查看持有狀態、頒發與收回徽章

### Modified Capabilities

- `badge-system`: 新增 revoke 機制（BadgeAward soft delete）、detail API、現有查詢排除已撤銷 award

## Impact

- Affected specs: `badge-system`（新增 revoke requirement、detail API requirement）、`badge-detail-modal`（新 spec）
- Affected code:
  - `src/gamification/badges/models.py` — BadgeAward 新增 revoked_at / revoked_by 欄位
  - `src/gamification/badges/service.py` — 新增 revoke_badge()，修改 award_badge() 和查詢以排除已撤銷
  - `src/gamification/badges/router.py` — 新增 detail / revoke endpoint
  - `src/templates/teacher/badges_manage.html` — 新增 detail modal UI + JS
  - `docs/security-notes.md` — 記錄新端點的安全設計
  - `tests/test_badges.py` — 新增 revoke / detail 測試
