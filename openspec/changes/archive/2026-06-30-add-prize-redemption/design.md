## Context

獎品（prizes）後端已具備完整 CRUD 與守門，但缺三塊：(1) 學生兌換扣點端點、(2) 任何 `/pages` UI 入口、(3) PATCH/DELETE 授權的 HTTP 級回歸測試。Handoff 05 經對抗式審查後，已把本案從誤判的「P1 安全」更正為「P3 產品範圍」，並由 stakeholder 拍板**補完功能（BUILD）**。

關鍵既有事實（已逐行查證）：

- `Prize`（`src/gamification/prizes/models.py`）欄位：`class_id`、`title`、`description`、`point_cost:int`、`visible:bool`、`prize_type`、`created_by`——**沒有庫存/stock 欄位**。
- 點數為 append-only ledger：`PointTransaction`（`src/gamification/points/models.py`），餘額 `get_balance(student_id)`（`src/gamification/points/service.py:5-10`）為**該學生全部交易之和，跨班全域（GLOBAL）**。
- 既有扣點手法：`deduct_points()` 插入負額交易（`service.py:42-60`）；`revoke_points()`（`service.py:63-87`）先讀 `get_balance` 再插入——這是既有、已記錄的 TOCTOU。
- docker-compose 的 Mongo 為 **standalone**，無多文件交易（multi-doc transactions）。
- 班級成員：`ClassMembership`（`src/core/classes/models.py`），`can_manage_class`（`src/core/classes/service.py:17-32`）為教師守門。
- 頁路由模式：badges router 用 `@router.get(...)` + `@webpage.page("...html")` + `get_page_user` + `build_page_context`（`src/gamification/badges/router.py:434-493`），不需動 `main.py`。
- P0 共用 Modal：`src/templates/shared/base.html` 提供 `Modal.confirm/alert/dialog`。

## Goals / Non-Goals

**Goals:**

- 提供學生兌換端點 `POST /classes/{class_id}/prizes/{prize_id}/redeem`，守門比照 badge membership/IDOR 模式，餘額不足回 4xx 且不扣點。
- 兌換成功只插入**單一**負額 `PointTransaction`，ledger entry 即為兌換紀錄（不新增 collection）。
- 提供學生獎品頁與教師獎品管理頁（皆掛在既有 prizes router 的 `@webpage.page` 路由），讓獎品可被檢視、兌換與經 UI 建立/管理。
- 補齊 handoff §5 的兩項缺漏授權測試與全套 redeem 測試。
- 把產品決策（BUILD）與兌換設計（全域餘額、ledger-as-record、TOCTOU 立場）記入 spec/design。

**Non-Goals:**

- **不**新增獎品庫存/stock 欄位或售罄邏輯（`Prize` 無此欄位，本版不引入）。
- **不**引入 replica-set / Mongo 多文件交易來消除 TOCTOU——維持與既有 ledger 一致的設計，殘餘 TOCTOU 記為已接受限制。
- **不**新增兌換專屬 collection 或兌換審核/出貨流程（線上/實體獎品的後續履約不在本版）。
- **不**改動 `src/main.py` 的 router 掛載；**盡量不**改動 `shared/base.html`。
- **不**改變 `get_balance` 的全域跨班語意（沿用既有行為）。

## Decisions

### 兌換端點掛在既有 prizes router 並重用 badge IDOR 守門模式

`POST /classes/{class_id}/prizes/{prize_id}/redeem` 新增於 `src/gamification/prizes/router.py`，兌換者由 `get_current_user`（JWT）解出的學生。守門順序：

1. `Prize.get(prize_id)`，不存在 → 404。
2. 校驗 `prize.class_id == 路徑 class_id`，否則 → 404/4xx（防跨班/他班獎品，比照 badge `badge.class_id == class_id`）。
3. 校驗 `prize.visible` 為真，否則 → 4xx（不可兌換不可見獎品）。
4. 校驗學生為該班 member：`ClassMembership.find_one(class_id, user_id)` 存在（任一角色即可檢視兌換頁，但兌換以 student member 為準），否則 → 403（比照 badge IDOR-001 的 membership 驗證）。
5. `get_balance(student_id) >= prize.point_cost`，否則 → 4xx insufficient-points，**不插入任何交易**。

**為何**：完全沿用 `docs/security-notes.md` 記載的 badge membership/IDOR 修復模式（PATCH/DELETE 由 `prize.class_id` 反推而非信任 caller），不發明新守門框架。

**替代方案**：另開 `core/redemption` 模組——否決，徒增模組且與既有 gamification 結構不一致。

### 兌換以單一負額 PointTransaction 作為紀錄（ledger-as-record）

兌換成功插入單筆 `PointTransaction(amount = -point_cost, source_event="prize_redemption", source_id=prize_id, class_id=prize.class_id, created_by=student_id)`。此 ledger entry **即**兌換紀錄，**不新增** collection。回傳兌換結果與 `get_balance` 重算後的新餘額。實作放在新檔 `src/gamification/prizes/service.py` 的 redeem service function，端點僅做守門與序列化（比照 points service/router 分層）。

**為何**：`PointTransaction` 已是 append-only 真實來源，`source_event` 已有多個列舉值（checkin/submission/teacher_deduct…），新增 `prize_redemption` 與既有風格一致；餘額永遠由交易和重算，無獨立 balance 欄位需同步。

**替代方案**：新增 `Redemption` collection——否決，與「餘額＝交易和、無額外狀態」的既有設計衝突，且 standalone Mongo 下跨 collection 寫入無交易保證。

### 並發/重複兌換採插入前再查餘額 + 前端 in-flight 鎖

扣點插入前緊鄰再呼叫一次 `get_balance` 做第二次餘額檢查（與 `revoke_points()` 同手法），降低重複點擊造成負餘額的視窗；前端「兌換」按鈕在請求進行中停用（in-flight disable），避免快速雙擊。standalone Mongo 無多文件交易，無法做到嚴格原子扣點，故**殘餘 TOCTOU 明文記為已接受限制**，與既有 ledger 的 TOCTOU 處置一致。

**為何**：handoff 明示「不要發明 replica-set/transactions 需求」；本決策與既有程式碼一致且最小變更。

**替代方案**：要求 Mongo replica set 開交易——否決（超出本版範疇且改動部署架構）；以 Redis 鎖序列化——否決（為單一功能引入跨服務鎖過重）。

### 學生與教師獎品頁掛在既有 router 的 @webpage.page 路由（不動 main.py）

- 學生頁：`GET /pages/classes/{class_id}/prizes`（`name="prizes_page"`，render `student/prizes.html`），用 `get_page_user` + `build_page_context`；列出該班 visible 獎品與 `point_cost`、顯示學生 `get_balance` 餘額、每獎品一顆「兌換」按鈕（P0 Modal 確認 → fetch POST redeem → 就地更新餘額與該列狀態、in-flight 停用）。
- 教師頁：`GET /pages/classes/{class_id}/prizes/manage`（`name="prizes_manage_page"`，render `teacher/prizes_manage.html`），守門 `can_manage_class`；列表＋建立（title/description/point_cost/visible）＋切換 visibility＋刪除，全部重用既有 create/list/patch/delete 端點。

**為何**：badges/points 頁路由都掛在各自 router（`badges/router.py:434-493`、`points/router.py:137`），已 `include_router` 於 app，新增頁路由不需碰 `main.py`。

### 導覽鏈結加在 dashboard 班級卡片，不改 base.html

於 `src/templates/student/dashboard.html` 既有「排行榜／積分管理」教師鏈結區塊（教師卡片）加「獎品管理」連到 `prizes_manage_page`；學生班級卡片加「兌換獎品」連到 `prizes_page`。盡量不動 `src/templates/shared/base.html`（側欄/底部導覽）。

**為何**：handoff 指定「PREFER not editing shared/base.html」，且既有積分/排行榜鏈結已在 dashboard 班級卡片，語意一致。

## Implementation Contract

**行為（兌換端點）**：`POST /classes/{class_id}/prizes/{prize_id}/redeem`

- 兌換者＝JWT 學生（`get_current_user`）。
- 守門全通過且 `get_balance(student) >= prize.point_cost` 時：插入**恰一筆** `PointTransaction`，`amount == -prize.point_cost`、`source_event == "prize_redemption"`、`source_id == prize_id`、`class_id == prize.class_id`、`created_by == student_id`；回傳 JSON 含兌換結果與重算後的 `new_balance`（== 兌換前餘額 − point_cost）。
- **失敗模式**（皆不得插入任何交易）：
  - prize 不存在 → 404。
  - `prize.class_id != path class_id` 或 `prize.visible == False` → 4xx（拒絕兌換）。
  - 學生非該班 member → 403。
  - `get_balance(student) < prize.point_cost` → 4xx insufficient-points。
- **並發**：插入前再查一次餘額；殘餘 TOCTOU 為已接受限制。

**介面（service）**：新檔 `src/gamification/prizes/service.py` 提供 redeem service function（輸入 student_id / prize / 重算餘額；負責第二次餘額檢查與插入負額交易、回傳 `(transaction, new_balance)` 或拋出 insufficient-points 錯誤），router 僅守門與序列化。

**介面（頁路由）**：

- `prizes_page` → `GET /pages/classes/{class_id}/prizes`，render `student/prizes.html`，context 至少含 visible 獎品清單（含 `id`/`title`/`description`/`point_cost`）、學生目前餘額、`class_id`、`build_page_context` 內容。
- `prizes_manage_page` → `GET /pages/classes/{class_id}/prizes/manage`，render `teacher/prizes_manage.html`，`can_manage_class` 守門，context 含該班全部獎品（含 `visible`）。

**前端行為**：學生頁「兌換」按鈕經 P0 `Modal.confirm` 確認 → `fetch` POST redeem → 成功就地更新顯示餘額與該列結果、失敗顯示錯誤訊息；請求進行中按鈕 `disabled`（in-flight）。

**驗收（acceptance）**：`tests/test_prizes.py` 涵蓋：

- redeem 成功 → 餘額下降 `point_cost`、恰新增一筆負額交易。
- 餘額不足 → 4xx 且交易數不變（無扣點）。
- 非 member 學生 → 403。
- 不可見或他班 prize → 兌換被拒（4xx），無扣點。
- PATCH `/prizes/{id}`、DELETE `/prizes/{id}` 跨教師（教師 A 帶教師 B 的 prize）→ 403。
- PATCH/DELETE 缺 `MANAGE_TASKS` → 403。
- 頁路由：學生頁 200 且只列 visible 獎品；教師管理頁 `can_manage_class` 守門。

**範圍邊界**：in scope＝redeem 端點＋service＋兩個頁路由＋兩個 template＋dashboard 鏈結＋上述測試。out of scope＝庫存欄位、兌換審核/出貨履約、Mongo 交易、`main.py`/`base.html` 結構變更、`get_balance` 語意變更。

## Risks / Trade-offs

- [殘餘 TOCTOU：兩個並發請求可能各自讀到足夠餘額而雙雙扣點，導致餘額短暫為負] → 插入前二次查餘額 + 前端 in-flight 鎖縮小視窗；明文記為已接受限制（與既有 `revoke_points` 一致，standalone Mongo 無交易）。
- [全域餘額跨班：學生 A 班賺的點可兌 B 班獎品] → 此為 `get_balance` 既有設計（GLOBAL），本版**刻意沿用**並在 spec 標明；不在本版改變語意以免回歸既有點數行為。
- [跨班兌換的「逐班分攤」副作用：扣點記在 `prize.class_id`，但授權卻是用全域餘額] → 兌換以全域 `get_balance` 授權，扣點交易卻完整記在兌換班級（`class_id == prize.class_id`）。因此一名在 A 班賺點、又是 B 班 member 的學生兌換 B 班獎品時，會在 B 班寫入一筆 `PointTransaction(class_id=B, amount=-cost)`，即使他在 B 班實際賺點為 0。這會牽動兩處**逐班（per-class）**統計：
  - **徽章資格**：badge DSL 的 `points` 變數是「同一 `student_id` 且同一 `class_id`」的交易和（`badges/service.py`、`badges/router.py`）。此負額會把 B 班的 per-class `points` 往下壓。但徽章門檻皆為正向 `points >= N`，故此副作用只會讓徽章**更難**達成，**絕不會**憑空鑄點或誤頒徽章；已落地的 `BadgeAward` 也不會被回溯撤銷。
  - **排行榜名次**：leaderboard 以同一全域 `get_balance` 排名（`leaderboard/router.py`），故任一班的兌換都會等量拉低該學生在**每一個**班級排行榜的餘額/名次。
  影響有界且與既有 `teacher_deduct`/`manual_revoke` 同樣會降低 per-class 點數的行為一致，亦符合 spec（`class_id == prize.class_id`），故本版**接受現狀、不改碼**。後續若要消除此分攤偏差，可評估：將兌換扣點分攤回「賺點所在班級」，或讓徽章門檻改以「累計賺得（lifetime-earned）」而非「當前餘額」為基準——皆超出本版範疇，另提 change 處理。
- [無庫存欄位 → 獎品可被無限兌換（只要有點）] → 本版以扣點為唯一稀缺性來源；庫存列為 Non-Goal，後續若需可另提 change。
- [前端 `| safe` / XSS] → 獎品 `title`/`description` 為使用者輸入，template 一律走 Jinja2 autoescape，前端就地更新用 `textContent`/escape，不對使用者內容用 `| safe`（遵 SEC-WATCH-001）。
