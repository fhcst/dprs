## Context

共用 Modal 元件定義於 `shared/base.html`，透過 `window.Modal` 提供 `dialog`/`confirm`/`alert`，全部經由同一個內部 `_show()` 與 `close()`，且共用單一 `#modal-overlay`/`#modal-body`。

現行 `close(callback)` 的順序是：隱藏 overlay → 清空 `#modal-body` → **才**呼叫 `callback`。對「訊息型」的 `confirm`/`alert`（callback 不讀 body）無害；但對「表單型」的 `dialog`（在 `onConfirm` 內讀取注入 body 的 `<input>`）會讀到 `null`、拋 TypeError，因 callback 為 async 而成為 unhandled rejection，後續 `fetch` 不送出。

E2E 已證實「建立班級」「加入班級」兩個 `Modal.dialog` 表單因此完全失效。這兩條是唯一能建立/加入班級的 UI 入口。

**重要約束（來自對抗式審查）**：約 8–9 個既有流程採「`Modal.confirm` 確認後，在 callback 內視結果再開 `Modal.alert`」。它們現在能運作，正是因為 confirm 在 callback 前已關閉。若把生命週期改動套用到**所有** Modal，會使這些後續 alert 射入仍開啟的 overlay 而互相覆寫——反而製造更大範圍 regression。

## Goals / Non-Goals

**Goals:**
- 讓 `Modal.dialog` 的 `onConfirm` 能在 body 仍存在時讀取欄位並送出請求。
- 定義 `dialog` 的 `onConfirm` 結果契約，涵蓋「成功關閉 / 成功保持開啟 / 驗證失敗保持開啟 / 錯誤保持開啟並顯示 in-modal 訊息」。
- 修復巢狀 modal 覆寫（badge 詳情中撤銷後 modal 消失）。
- **不** regress 既有 `Modal.confirm`/`Modal.alert` 流程。

**Non-Goals:**
- 不更動 Modal 視覺樣式或 ARIA 語意（`shared-modal` a11y 規範不變）。
- 不將表單 modal 改寫為獨立頁面。
- 不處理其他 E2E findings（empty_state、login next、依賴升級）。

## Decisions

### Decision 1: Scope the close-lifecycle change to dialog modals only
僅對「表單型」`Modal.dialog` 改變生命週期；`Modal.confirm`/`Modal.alert`（訊息型、callback 不讀 body）維持現行「先關閉再 callback」語意不變。判別方式：`Modal.dialog` 設定一個顯式 `_isForm: true` 標記，內部 `_isDialog(opts)` 僅以該標記辨識表單型 dialog。
- **理由**：只有 dialog 會在 `onConfirm` 讀取 body 欄位；confirm/alert 不會。如此可精準修復 2 個壞掉流程，同時**完全不動**那 8–9 個 `confirm→alert` 流程（皆為 `Modal.confirm`），避免引入新 regression。
- **判別子實作備註（doc 對齊 impl）**：原先設想以「`opts.html` 是否存在」判別，但 `Modal.alertHtml` 也會經由 `_show({ html })` 注入 HTML，若以 body 存在與否判別會把 `alertHtml` 誤判為表單 dialog；因此改採顯式 `_isForm` 標記，只有 `Modal.dialog` 帶此旗標，`alertHtml`/`alert`/`confirm` 皆不帶，判別精準且不依賴 body 內容。
- **替代方案（否決）**：對所有 Modal 統一改成「callback 完成後才關閉」——會使 confirm→alert 後續 alert 覆寫仍開啟的 confirm（對抗式審查已驗證的反向 regression）。

### Decision 2: onConfirm return value controls dialog close timing
`Modal.dialog` 的 `onConfirm`（async）以**回傳值**表達是否關閉：解析為非 `false`（含 `undefined`）→ 關閉並清空 body；回傳 `false` 或 throw/reject → **保持開啟**、保留 body（含 in-modal 訊息節點）。框架以 try/catch 包住 callback，throw 視為「保持開啟」。
- **理由**：以單一契約涵蓋全部既有模式——建立班級（成功 `location.reload()`；空輸入/錯誤回傳 `false` 保持開啟）、加入班級（成功顯示 in-modal 訊息、回傳 `false` 保持開啟）。
- **替代方案（否決）**：拆成 `onConfirmSuccess`/`onConfirmError` 兩個 callback——對既有呼叫端改動更大、語意更碎。

### Decision 3: Handle nested modals to prevent overlay overwrite
針對「`dialog` 開啟中再開 `confirm`」（badge 詳情撤銷）導入巢狀處理：優先採輕量 modal 堆疊（push/pop 保存上一層內容與狀態），關閉上層後還原下層；若堆疊複雜度過高，退而採「單一已知巢狀點」守門（撤銷前妥善保存/還原 badge 詳情內容，避免寫入已隱藏 body）。
- **理由**：修復 NEW-1「撤銷後詳情 modal 消失」，並讓未來巢狀場景安全。
- **替代方案（否決）**：完全禁止巢狀——會限制既有 UX（詳情中直接撤銷）。

## Implementation Contract

**行為（dialog 表單）**
- 建立班級：於 dialog 輸入合法名稱並確認 → 送出建立班級請求；成功後 dashboard 反映新班級；名稱為空 → dialog 保持開啟並聚焦名稱欄位；伺服器錯誤 → dialog 保持開啟並顯示 in-modal 錯誤文字；**console 不得出現 uncaught promise rejection**。
- 加入班級：輸入邀請碼並確認 → 送出加入請求；成功 → 顯示 in-modal 成功訊息且 dialog 保持開啟；失敗 → in-modal 顯示錯誤、保持開啟。

**介面契約（`Modal.dialog`）**
- `onConfirm` 為 async；其 Promise 解析為非 `false` → 框架關閉並清空 dialog；解析為 `false` 或 reject/throw → 框架不關閉、保留 body 節點。
- dialog 的 body（含任何 in-modal 訊息元素）在 dialog 實際關閉前都保留在 DOM。

**未變更行為（回歸保證）**
- `Modal.confirm`/`Modal.alert` 維持「確認/關閉後再執行 callback」；callback 內若再開 `Modal.alert` 須正確顯示（無覆寫）。

**巢狀行為**
- 於 badge 詳情 modal 內撤銷：確認後套用撤銷，且 badge 詳情內容維持一致、**不消失**。

**驗收**
- E2E：建立班級、加入班級流程成功（含成功/空輸入/錯誤三路徑）。
- 回歸：Decision 1 所述全部 `Modal.confirm→Modal.alert` 流程（班級封存/隱藏、使用者刪除、成員審核/移除、模板封存、觸發規則刪除、徽章刪除）後續 alert 正確顯示。
- badge 撤銷後詳情 modal 不消失。
- 全程無 console uncaught promise rejection。

**範圍邊界**
- In scope：`shared/base.html` Modal `_show`/`close` 生命週期與巢狀處理；`dashboard.html` 建立/加入班級 `onConfirm` 對齊新契約；`badges_manage.html` 巢狀撤銷修復。
- Out of scope：Modal 視覺/ARIA、其他 findings、表單改頁面化。

## Risks / Trade-offs

- [更動全站共用 Modal 可能波及所有頁面] → 以 Decision 1 將行為改動限縮在 dialog 分支；交付前對每個 `Modal.*` 呼叫端做回歸。
- [巢狀 modal 堆疊增加複雜度] → 若堆疊風險過高，先以單一已知巢狀點（badge 撤銷）守門，通用堆疊另案處理。
- [dialog `onConfirm` 契約改變需同步更新建立/加入班級 handler] → 兩處一併更新並於 spec 記錄契約，避免半套。

## Migration Plan

- 純前端模板/JS 變更，無資料 migration。dev 模式（`fastapi dev`）會自動 reload；正式環境隨 image rebuild 生效。
- Rollback：還原 `shared/base.html` 與受影響模板即可。

## Open Questions

- Decision 3 採通用 modal 堆疊或僅 badge 巢狀守門，依實作複雜度於 apply 階段定案。
- ~~「保持開啟」之 sentinel 採回傳 `false` 或結構化旗標（如 `{ keepOpen: true }`），實作時擇一並於 spec/註解固定。~~ **已定案**：同時支援回傳 `false`（back-compat）與顯式結構化哨兵 `Modal.KEEP_OPEN`（`{ __modalKeepOpen: true }`）；兩者皆「保持開啟」，其餘解析值關閉。已於 spec.md「Dialog form modals…」需求與 `base.html` 註解固定。
