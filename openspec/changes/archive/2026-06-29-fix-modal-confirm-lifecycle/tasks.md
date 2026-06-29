## 1. Modal dialog 生命週期基礎（`shared/base.html`）

- [x] 1.1 實作 **Decision 1: Scope the close-lifecycle change to dialog modals only** — 於 `_show()`/`_onConfirm()`/`_popOrHide()` 以顯式 `_isForm` 標記（`_isDialog(opts)` 回傳 `!!(opts && opts._isForm)`，僅 `Modal.dialog` 帶此旗標）判別 dialog，而非以 `opts.html` 是否存在判別（`Modal.alertHtml` 也會注入 `html`，會被誤判）；dialog 確認時不再於 callback 前清空 `#modal-body`，`Modal.confirm`/`Modal.alert` 維持原「先關閉再 callback」。**行為**：建立班級 dialog 確認後 body 仍在 DOM，`onConfirm` 能讀到輸入欄位。**驗證**：E2E（chrome-devtools）確認後 console 無 uncaught promise rejection，且送出 `POST /classes`。
- [x] 1.2 實作 **Decision 2: onConfirm return value controls dialog close timing** — 以 try/catch 包住 dialog 的 `onConfirm`；回傳非 `false`→關閉並清空 body，回傳 `false`/throw/reject→保持開啟並保留 body。對應 **Requirement: Dialog form modals invoke the confirm callback before teardown**。**行為**：dialog 是否關閉由回傳值決定、錯誤不外溢為 unhandled rejection。**驗證**：手動/單元 — 回傳 `false` 保持開啟、resolve 關閉、throw 時 console 無 unhandled rejection。

## 2. 巢狀 modal 分層（`shared/base.html`）

- [x] 2.1 實作 **Decision 3: Handle nested modals to prevent overlay overwrite** — 支援自某 modal callback 內開啟另一 modal 而不破壞底層內容，關閉上層後還原底層；對應 **Requirement: Nested modals preserve the underlying modal content**。**行為**：巢狀開啟時底層內容不被覆寫、關閉上層後還原。**驗證**：手動於 badge 詳情內觸發二層 modal，關閉後底層內容仍在。

## 3. 對齊建立／加入班級 onConfirm 契約（`student/dashboard.html`）

- [x] 3.1 將 `openCreateClassModal` 對齊 **Requirement: Dialog form modals invoke the confirm callback before teardown** — 成功 `location.reload()`；名稱為空聚焦欄位並回傳 `false`；`POST /classes` 非 201 時於 `#create-class-error` 顯示錯誤並回傳 `false`。**行為**：建立班級成功後 dashboard 出現新班級；失敗/空輸入 dialog 保持開啟並顯示提示。**驗證**：E2E 建立班級 → `POST /classes` 201、班級出現於「我的班級」；空名稱與錯誤路徑 dialog 不關閉。
- [x] 3.2 將 `openJoinClassModal` 對齊同一 Requirement — 加入成功顯示 in-modal 成功訊息且 dialog 保持開啟（回傳 `false`）。**行為**：輸入邀請碼加入成功後於 dialog 內顯示成功訊息、不關閉。**驗證**：手動/E2E 以有效邀請碼加入 → in-modal 成功訊息出現、dialog 維持開啟。

## 4. badge 巢狀撤銷修復（`teacher/badges_manage.html`）

- [x] 4.1 [P] 修復 `revokeFromDetail`/`renderDetailModal`，對應 **Requirement: Nested modals preserve the underlying modal content** 與 **Decision 3: Handle nested modals to prevent overlay overwrite** — 自 badge 詳情 modal 內撤銷後，詳情內容維持可見一致。**行為**：撤銷後 badge 詳情 modal 不消失/不空白、撤銷結果反映於列表。**驗證**：手動/E2E 於詳情內撤銷一枚徽章 → 詳情仍可見且該生移至未頒發區。

## 5. 回歸驗證（不得 regress 既有 confirm 流程）

- [x] 5.1 回歸 **Decision 1** 所保留的全部 `Modal.confirm → Modal.alert` 流程：`admin/classes_list.html`（封存/隱藏）、`admin/users_list.html`（刪除）、`teacher/class_members.html`（審核/移除）、`teacher/templates_list.html`（封存）、`teacher/trigger-rules.html`（刪除）、`teacher/badges_manage.html`（刪除）。**行為**：確認後的後續 `Modal.alert` 正確顯示、無覆寫/空白。**驗證**：逐一手動觸發各流程的失敗/成功路徑，確認 alert 正常顯示。
- [x] 5.2 整體 E2E 重跑建立班級、加入班級，並確認全程 **無 console uncaught promise rejection**。**行為**：兩條班級入口流程 UI 可用、班級功能樹恢復可達。**驗證**：chrome-devtools E2E 走完流程、`list_console_messages` 無 error/unhandled rejection。
