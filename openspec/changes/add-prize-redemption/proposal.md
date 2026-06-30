## Why

獎品（prizes）後端 CRUD 端點已掛載於 app 且守門完整（`src/main.py:160`、`src/gamification/prizes/router.py`），但**沒有任何 `/pages` 路由、沒有 template、也沒有兌換（redemption）扣點端點**——學生看不到獎品、也無法用累積的積分兌換，導致整個點數經濟（point economy）斷在最後一哩。Handoff 05 已將此案從誤判的「P1 安全」下修為「P3 產品範圍」，並由 stakeholder 拍板：**補完功能（BUILD）**。本提案落實此決策，把獎品從「API-only 半成品」補成「學生可兌換、教師可經 UI 管理」的完整功能。

## What Changes

- 新增 redemption service function 與端點 `POST /classes/{class_id}/prizes/{prize_id}/redeem`（兌換者＝JWT 解出的學生），守門比照 badge IDOR 模式：校驗 `prize.class_id == 路徑 class_id`、`prize.visible`、學生為該班 member、餘額（全域 `get_balance`）足夠；成功時插入**單一**負額 `PointTransaction`（`source_event="prize_redemption"`、`source_id=prize_id`），ledger entry 即兌換紀錄，回傳兌換結果與新餘額。
- 並發/重複兌換防護：插入前緊鄰再查一次餘額（與既有 `revoke_points()` 的 TOCTOU 處置一致），並搭配前端 in-flight 按鈕停用；殘餘 TOCTOU 記為**已接受的限制**（standalone Mongo 無多文件交易，與既有 ledger 設計一致）。
- 新增學生獎品頁 `GET /pages/classes/{class_id}/prizes`（掛在既有 prizes router 的 `@webpage.page` 路由，比照 badges 頁路由，不動 `main.py`）：列出該班 visible 獎品與 `point_cost`、顯示學生目前餘額、每個獎品一顆「兌換」按鈕（用 P0 共用 Modal 確認 → POST redeem → 就地更新餘額與結果）。
- 新增教師獎品管理頁 `GET /pages/classes/{class_id}/prizes/manage`（重用既有 create/list/patch/delete 端點）：列表、建立（title/description/point_cost/visible）、切換 visibility、刪除，讓獎品可經 UI 建立。
- 從既有班級情境（dashboard 班級卡片既有「排行榜／積分管理」鏈結附近）連到上述兩頁，盡量不改動 `shared/base.html`。
- 補測試：兩項目前缺的 HTTP 級授權測試（PATCH/DELETE `/prizes/{id}` 跨教師 IDOR → 403、缺 `MANAGE_TASKS` → 403），以及 redeem 測試（成功扣 `point_cost` 且餘額下降、餘額不足拒絕且不扣點、非 member → 403、不可見/他班獎品 → 拒絕）。

## Non-Goals

詳見 design.md 的 Goals / Non-Goals 一節。

## Capabilities

### New Capabilities

- `prize-redemption`: 學生用累積積分兌換獎品的完整流程——redemption service function、`POST /classes/{class_id}/prizes/{prize_id}/redeem` 端點（守門、全域餘額檢查、ledger-as-record、TOCTOU 處置）、學生獎品頁（列表＋餘額＋兌換按鈕，就地更新）。

### Modified Capabilities

- `prize-preview`: 既有獎品 CRUD/檢視能力新增教師獎品管理 HTML 頁（`/pages/classes/{class_id}/prizes/manage`，重用既有端點），並將既有 PATCH/DELETE 端點的擁有權（cross-teacher IDOR）與 `MANAGE_TASKS` 權限守門明文化為 normative 需求並補回歸測試。

## Impact

- **新增程式碼**：`src/gamification/prizes/service.py`（新檔，redeem service）、`src/gamification/prizes/router.py`（redeem 端點＋兩個 `@webpage.page` 頁路由）、`src/templates/student/prizes.html`、`src/templates/teacher/prizes_manage.html`、`src/templates/student/dashboard.html`（導覽鏈結）。
- **新增測試**：`tests/test_prizes.py`（redeem 成功/不足/非 member/他班/不可見、PATCH/DELETE IDOR 403、缺權限 403）。
- **資料模型**：不新增 collection；兌換紀錄沿用 `pointtransactions`（`PointTransaction`）。
- **相依**：依賴 P0 共用 Modal（`src/templates/shared/base.html` 既有 `Modal`）、`get_balance`/ledger（`src/gamification/points/service.py`）、`can_manage_class`/`ClassMembership`（`src/core/classes/`）。
- **無 `main.py` 變更**：頁路由掛在既有已 include 的 prizes router。
