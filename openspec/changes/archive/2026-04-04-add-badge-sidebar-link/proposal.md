## Why

徽章管理功能已完整實作（models、service、API、教師管理頁面），但教師 sidebar 缺少「徽章管理」連結。目前教師無法從 UI 存取 `/pages/classes/{class_id}/badges`，只能手動輸入 URL。

## What Changes

- 在教師 sidebar 的 class tool links 區塊（`base.html` 第 212-264 行）加入「徽章管理」導航連結，指向 `badges_manage_page` route
- 連結位置放在「積分管理」之後（或「排行榜」與「積分管理」之間，依設計決定）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `badge-system`：新增 sidebar 導航入口的需求，確保教師可從班級管理側欄存取徽章管理頁面

## Impact

- 受影響檔案：`src/templates/shared/base.html`（sidebar 導航區塊）
- 受影響 specs：`badge-system`（補充導航需求）
