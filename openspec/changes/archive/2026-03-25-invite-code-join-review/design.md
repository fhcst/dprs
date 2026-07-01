## Context

目前系統中，學生透過邀請碼加入班級（`POST /classes/join`）會直接建立 `ClassMembership`，無需教師審核。這造成安全風險：任何取得邀請碼的人都能立即成為班級成員。現有資料模型只有 `Class` 和 `ClassMembership`，沒有「申請中」的中間狀態。

相關現有程式碼：
- `src/core/classes/models.py` — `Class` 與 `ClassMembership` Beanie Document
- `src/core/classes/router.py` — `POST /classes/join` 端點直接呼叫 `join_class_by_code()`
- `src/core/classes/service.py` — `join_class_by_code()` 直接建立 membership
- `src/core/system/models.py` — `SystemConfig` 單例文件（目前只有 `site_name`, `admin_email`）

## Goals / Non-Goals

**Goals:**

- 將邀請碼加入流程改為「申請 → 教師審核 → 加入」三步流程
- 新增獨立 `JoinRequest` collection 管理申請狀態，不污染現有 `ClassMembership`
- 提供學生端申請 UI 與教師端審核 UI
- 加入速率限制與冷卻機制等安全防護
- `SystemConfig` 新增可設定的拒絕冷卻時間

**Non-Goals:**

- 不修改公開班級的加入流程（`POST /classes/{class_id}/join` 保持直接加入）
- 不實作通知系統（教師不會收到即時通知，需手動查看）
- 不實作批次審核功能（逐一 approve/reject）
- 不修改教師批次邀請流程（`POST /classes/{class_id}/invite/batch` 仍直接加入）

## Decisions

### Decision: 獨立 JoinRequest Collection（而非修改 ClassMembership）

新增獨立 `JoinRequest` Beanie Document，欄位：
- `class_id: str` — 目標班級
- `user_id: str` — 申請學生
- `status: Literal["pending", "approved", "rejected"]` — 申請狀態
- `requested_at: datetime` — 申請時間
- `reviewed_at: datetime | None` — 審核時間
- `reviewed_by: str | None` — 審核教師 ID
- `invite_code_used: str` — 使用的邀請碼

MongoDB 唯一索引：`(class_id, user_id, status="pending")` 確保同一學生對同一班級只能有一筆 pending 申請。

**為什麼不修改 ClassMembership：**
- ClassMembership 語意明確（已加入的成員），加入 pending 狀態會破壞所有依賴「membership = 已加入」的查詢
- JoinRequest 有自己的生命週期（申請、審核、冷卻），與 membership 語意不同
- 分離後可獨立查詢/清理過期申請，不影響成員管理效能

### Decision: POST /classes/join 行為變更為建立 JoinRequest

原有 `POST /classes/join` 端點行為從「直接建立 ClassMembership」改為「建立 JoinRequest(pending)」。這是 **BREAKING CHANGE**。

流程變更：
1. 學生提交邀請碼 → 驗證邀請碼有效性 → 檢查是否已是成員 → 檢查是否有 pending 申請 → 檢查冷卻期 → 建立 `JoinRequest(pending)`
2. 教師在 class_members 頁面看到待審核列表 → 點擊 approve/reject
3. Approve → 建立 `ClassMembership` + 更新 `JoinRequest.status = "approved"`
4. Reject → 更新 `JoinRequest.status = "rejected"` + 記錄時間（用於冷卻計算）

新增端點：
- `GET /classes/{class_id}/join-requests` — 教師查看待審核申請（需 `can_manage_class` 權限）
- `PATCH /classes/{class_id}/join-requests/{id}/review` — 教師審核（approve/reject）

### Decision: 拒絕冷卻機制透過 SystemConfig 設定

`SystemConfig` 新增欄位 `join_request_reject_cooldown_hours: int = 24`：
- 學生被拒絕後，需等待此時數才能重新申請同一班級
- 設為 `0` 表示不限制（可立即重新申請）
- 冷卻計算方式：查詢該 (class_id, user_id) 最近一筆 rejected 的 `reviewed_at`，若距今未超過冷卻時數則拒絕申請

此設定在 `PUT /admin/system` 端點中一併可更新，不需新增獨立 API。

### Decision: 安全防護策略

1. **速率限制**：`POST /classes/join-request` 端點加上 5 次/分/IP 的 rate limit（使用現有 slowapi 機制）
2. **身份限制**：僅 `identity_tag = "student"` 的使用者可提交加入申請
3. **唯一約束**：MongoDB partial unique index `(class_id, user_id)` where `status = "pending"` 確保不會重複申請
4. **邀請碼暴力破解防護**：透過上述 rate limit 間接防護，不需額外機制

### Decision: 學生端 UI — 按鈕觸發 Modal 表單

學生 dashboard 新增「加入班級」按鈕（樣式參考教師端「建立班級」按鈕），點擊後彈出 Modal：
- 內含一個邀請碼輸入欄位
- 提交後呼叫 `POST /classes/join-request`
- 成功顯示「申請已送出，等待教師審核」訊息
- 失敗顯示對應錯誤（已申請過、冷卻中、已是成員等）

### Decision: 教師端 UI — class_members 頁面新增待審核區塊

在現有 `class_members.html` 頁面頂部（成員列表之前）新增「待審核」區塊：
- 呼叫 `GET /classes/{class_id}/join-requests` 載入 pending 申請列表
- 每筆申請顯示學生資訊、申請時間、使用的邀請碼
- 每筆申請旁有「核准」與「拒絕」按鈕
- 操作後呼叫 `PATCH /classes/{class_id}/join-requests/{id}/review`
- 無待審核申請時顯示空狀態提示

## Risks / Trade-offs

- **[BREAKING CHANGE] 現有 `POST /classes/join` 行為變更** → 前端呼叫此端點的地方需同步更新回應處理（從直接加入改為「申請已送出」）。由於系統為單體應用（Jinja2 模板 + HTMX），前後端同步部署，風險可控。

- **[審核延遲] 學生無法立即加入班級** → 這是設計目標而非風險，但需確保 UI 清楚告知學生「等待審核」狀態。教師若未及時審核，學生體驗會受影響。未來可考慮加入通知機制。

- **[資料增長] JoinRequest 紀錄持續累積** → rejected/approved 的歷史紀錄會持續增長。短期內資料量不大，不需特別處理。未來可考慮定期清理已完成的紀錄。

- **[冷卻繞過] 學生可更換帳號繞過冷卻** → 冷卻機制基於 user_id，無法防止同一個人用不同帳號申請。但結合教師審核機制，此風險可接受。

## Migration Plan

1. 新增 `JoinRequest` model 並在 Beanie `init_beanie` 中註冊
2. 建立 MongoDB 索引（migration script）：`(class_id, user_id)` partial unique index where `status = "pending"`
3. 更新 `SystemConfig` model 新增 `join_request_reject_cooldown_hours` 欄位（有預設值 24，向後相容）
4. 修改 `POST /classes/join` 端點邏輯
5. 新增審核相關 API 端點
6. 更新前端模板

回滾策略：若需回滾，將 `POST /classes/join` 恢復為直接建立 membership。已建立的 `JoinRequest` 紀錄可保留不影響系統運作。

## Open Questions

（無 — 所有技術決策已在討論階段確認）
