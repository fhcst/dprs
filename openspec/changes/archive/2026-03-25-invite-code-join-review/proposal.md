## Why

學生端目前沒有 UI 可以輸入邀請碼加入班級。後端 API 雖然存在，但加入流程是直接成為成員，缺乏教師審核機制，有安全風險（任何拿到邀請碼的人都能直接加入）。

## What Changes

- 新增學生端「輸入邀請碼」按鈕 + Modal 表單
- 將邀請碼加入流程改為「申請 → 教師審核 → 加入」
- 新增獨立 `JoinRequest` collection（status: pending/approved/rejected）
- 教師端 class_members 頁新增「待審核」區塊，支援 approve/reject 操作
- `SystemConfig` 新增 `join_request_reject_cooldown_hours` 設定（預設 24h，0=不限）
- 安全防護：rate limit（5 次/分/IP）、唯一約束（同一 class+user 只允許一筆 pending）、僅 student identity_tag 可申請

## Capabilities

### New Capabilities

- `join-request-review`: 邀請碼加入申請與教師審核流程（JoinRequest model、API endpoints、學生申請 UI、教師審核 UI）

### Modified Capabilities

- `class-management`: 邀請碼加入行為從「直接加入」改為「建立 JoinRequest」，新增審核相關 API
- `system-config`: 新增 `join_request_reject_cooldown_hours` 全域設定欄位

## Impact

- 受影響程式碼：`src/core/classes/service.py`、`src/core/classes/router.py`、`src/core/classes/models.py`、`src/core/system/models.py`、`src/core/system/router.py`
- 受影響 UI：`src/templates/teacher/class_members.html`、新增學生端 Modal 元件
- 新增 API：`POST /classes/join-request`、`GET /classes/{class_id}/join-requests`、`PATCH /classes/{class_id}/join-requests/{id}/review`
- **BREAKING**：`POST /classes/join`（邀請碼加入）行為變更——不再直接建立 membership，改為建立 JoinRequest
