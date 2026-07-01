## Why

共用 Modal 元件（`shared/base.html` 的 `window.Modal`）在「確認」時，`close()` 會**先清空** modal body（`bodyEl.innerHTML = ''`）、**再呼叫** `onConfirm` callback。因此凡是在 `onConfirm` 內讀取 modal body 欄位的彈窗表單，都會讀到 `null`、拋 TypeError，且因 callback 為 async 而變成 uncaught promise rejection、後續 `fetch` 從未送出。

實測（E2E）證實「建立班級」與「加入班級」兩個彈窗表單因此**完全失效**且無任何錯誤提示。這兩條是唯一能建立／加入班級的 UI 路徑，等於 **UI 上無法建立任何班級** → 整棵班級相關功能樹（模板、提交、點名、徽章、排行榜、動態、觸發規則）全部無法經 UI 觸及。屬阻斷性 P0 缺陷，須優先修復。

## What Changes

- **重設表單 Modal 的確認生命週期**：確認時不再於 callback 前清空 body；改為讓 async `onConfirm` 在 body 完整時執行，待其結果決定關閉/清空時機（**BREAKING**：僅改變表單型 `Modal.dialog` 既有的「先關閉再 callback」順序；訊息型 `Modal.confirm`/`Modal.alert` 維持現行順序、語意不變）。
- **定義 callback 契約**，涵蓋現有全部模式：成功並關閉、成功但保持開啟（如加入班級顯示 in-modal 成功訊息）、驗證失敗保持開啟、錯誤保持開啟並顯示 in-modal 錯誤。
- **解決巢狀 modal 覆寫**：全站僅單一 `#modal-overlay`/`#modal-body`；新生命週期會使「`confirm` 確認後再開 `Modal.alert`」的既有流程，在 confirm 仍開啟時射入同一 overlay 而互相覆寫。須導入 modal 堆疊或守門，並一併修復 badge 詳情「撤銷後 modal 消失」（NEW-1）。
- **修正並回歸所有受影響呼叫端**：建立班級、加入班級，以及約 8–9 個 `confirm→alert` 流程。

## Non-Goals

- 不重寫 Modal 的視覺樣式或 ARIA 語意（`shared-modal` 之 a11y 規範維持不變）。
- 不把彈窗表單改寫成獨立頁面表單（維持 modal 互動模式）。
- 不處理其他 findings（BUG-1 empty_state、BUG-4 login next、依賴升級等），各有獨立提案。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `modal-system`: 新增/修改關於「確認 callback 生命週期」與「巢狀 modal 行為」的需求——確認時 callback 須在 modal body 仍存在時執行；modal 僅在 callback 解析後（或由 callback 決定）才關閉/清空；同時開啟多層 modal 時不得互相覆寫內容。

## Impact

- Affected specs: `modal-system`（modified，需 delta spec）
- Affected code:
  - `src/templates/shared/base.html` — Modal `_show()`/`close()` 生命週期、巢狀處理
  - `src/templates/student/dashboard.html` — 建立班級（`openCreateClassModal`）、加入班級（`openJoinClassModal`）callback 契約對齊
  - `src/templates/teacher/badges_manage.html` — `revokeFromDetail`/`renderDetailModal` 巢狀詳情修復
  - `confirm→alert` 呼叫端回歸：`src/templates/admin/classes_list.html`、`src/templates/admin/users_list.html`、`src/templates/teacher/class_members.html`、`src/templates/teacher/templates_list.html`、`src/templates/teacher/trigger-rules.html`
- 來源：E2E 測試 `.spectra/e2e-tests/20260628-234059/`（`report.md`、`adversarial-review.md`）
