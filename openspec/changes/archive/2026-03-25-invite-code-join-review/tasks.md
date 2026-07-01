## 1. 資料模型與資料庫遷移

- [x] 1.1 [P] 建立 `JoinRequest` Beanie Document model（實作 Decision: 獨立 JoinRequest Collection（而非修改 ClassMembership）），含 `class_id`, `user_id`, `status`, `requested_at`, `reviewed_at`, `reviewed_by`, `invite_code_used` 欄位，對應 Requirement: JoinRequest data model
- [x] 1.2 [P] 更新 `SystemConfig` model 新增 `join_request_reject_cooldown_hours: int = 24` 欄位（實作 Decision: 拒絕冷卻機制透過 SystemConfig 設定），對應 Requirement: SystemConfig document stores global settings
- [x] 1.3 建立 MongoDB migration script，為 `join_requests` collection 建立 `(class_id, user_id)` partial unique index（where `status = "pending"`），對應 Requirement: JoinRequest data model
- [x] 1.4 在 `init_beanie` 註冊 `JoinRequest` Document model

## 2. 測試先行 — 單元測試與整合測試

- [x] 2.1 [P] 撰寫 `JoinRequest` model 測試：建立、唯一約束驗證、狀態轉換（對應 Requirement: JoinRequest data model）
- [x] 2.2 [P] 撰寫學生提交加入申請 API 測試：有效邀請碼、無效邀請碼、已是成員、重複 pending、冷卻期內、冷卻期為 0、非 student 身份（對應 Requirement: Student submits join request via invite code）
- [x] 2.3 [P] 撰寫速率限制測試：5 次/分以內通過、第 6 次回傳 429（對應 Requirement: Rate limiting on join request endpoint）
- [x] 2.4 [P] 撰寫教師查看待審核列表 API 測試：有 pending 請求、空列表、未授權（對應 Requirement: Teacher views pending join requests）
- [x] 2.5 [P] 撰寫教師審核 API 測試：approve 建立 membership、reject 記錄冷卻、審核非 pending、未授權、不存在（對應 Requirement: Teacher reviews join request）
- [x] 2.6 [P] 撰寫邀請碼加入行為變更測試：`POST /classes/join` 建立 JoinRequest 而非 ClassMembership（對應 Requirement: Student joins a class）
- [x] 2.7 [P] 撰寫 SystemConfig 更新 API 測試：更新 cooldown 欄位、設為 0、負值回傳 422（對應 Requirement: System config update API）

## 3. 後端 Service 層實作

- [x] 3.1 實作 `create_join_request()` service 函式：驗證邀請碼、檢查已加入、檢查 pending、檢查冷卻期、建立 JoinRequest（實作 Decision: POST /classes/join 行為變更為建立 JoinRequest），對應 Requirement: Student submits join request via invite code
- [x] 3.2 實作 `get_pending_join_requests(class_id)` service 函式：查詢該班級所有 pending JoinRequest 並附帶學生資訊，對應 Requirement: Teacher views pending join requests
- [x] 3.3 實作 `review_join_request(join_request_id, action, reviewer_id)` service 函式：approve 時建立 ClassMembership 並更新狀態、reject 時更新狀態與 reviewed_at，對應 Requirement: Teacher reviews join request

## 4. 後端 Router 層實作

- [x] 4.1 新增 `POST /classes/join-request` 端點，呼叫 `create_join_request()`，僅允許 student identity_tag（實作 Decision: 安全防護策略），對應 Requirement: Student submits join request via invite code
- [x] 4.2 為 `POST /classes/join-request` 端點加上 slowapi 速率限制（5 次/分/IP），對應 Requirement: Rate limiting on join request endpoint
- [x] 4.3 新增 `GET /classes/{class_id}/join-requests` 端點，需 `can_manage_class` 授權，對應 Requirement: Teacher views pending join requests
- [x] 4.4 新增 `PATCH /classes/{class_id}/join-requests/{id}/review` 端點，需 `can_manage_class` 授權，對應 Requirement: Teacher reviews join request
- [x] 4.5 修改 `POST /classes/join` 端點行為：從直接建立 membership 改為呼叫 `create_join_request()`（BREAKING CHANGE），對應 Requirement: Student joins a class
- [x] 4.6 更新 `PUT /admin/system` 端點接受 `join_request_reject_cooldown_hours` 欄位並驗證非負整數，對應 Requirement: System config update API

## 5. 前端 UI 實作

- [x] 5.1 學生端 dashboard 新增「加入班級」按鈕與 Modal 表單（實作 Decision: 學生端 UI — 按鈕觸發 Modal 表單），含邀請碼輸入欄位、提交按鈕、成功/錯誤訊息顯示，對應 Requirement: Student join request UI
- [x] 5.2 教師端 class_members 頁面新增「待審核」區塊（實作 Decision: 教師端 UI — class_members 頁面新增待審核區塊），顯示 pending JoinRequest 列表，含核准/拒絕按鈕與空狀態提示，對應 Requirement: Teacher pending review UI section
- [x] 5.3 更新管理員系統設定頁面，新增 `join_request_reject_cooldown_hours` 欄位至表單中

## 6. 驗證與收尾

- [x] 6.1 執行全部測試套件確認通過（含新增與既有測試）
- [x] 6.2 手動端對端測試完整流程：學生申請 → 教師審核（approve/reject）→ 驗證結果
- [x] 6.3 驗證 BREAKING CHANGE：確認 `POST /classes/join` 不再直接建立 membership
