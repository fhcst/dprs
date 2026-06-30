## 1. 兌換 service 與端點（後端）

- [x] 1.1 在新檔 `src/gamification/prizes/service.py` 實作 redeem service function：依「兌換以單一負額 PointTransaction 作為紀錄（ledger-as-record）」決策，成功時插入恰一筆 `PointTransaction`（`amount = -point_cost`、`source_event="prize_redemption"`、`source_id=prize_id`、`class_id=prize.class_id`、`created_by=student_id`）並回傳重算後餘額；依「並發/重複兌換採插入前再查餘額 + 前端 in-flight 鎖」決策，插入前緊鄰再呼叫 `get_balance` 做第二次餘額檢查、不足則中止不插入。落實 spec「Redemption is recorded as a single point-ledger transaction」與「Concurrent redemption re-checks balance before deduction」。驗證：`tests/test_prizes.py` 中成功兌換僅新增一筆負額交易、且 service 在餘額不足時不插入交易。
- [x] 1.2 在 `src/gamification/prizes/router.py` 新增端點 `POST /classes/{class_id}/prizes/{prize_id}/redeem`，兌換者＝`get_current_user` 解出的學生；依「兌換端點掛在既有 prizes router 並重用 badge IDOR 守門模式」決策，依序守門：載入 prize（404）、`prize.class_id == 路徑 class_id`、`prize.visible`、學生為該班 `ClassMembership` member（否則 403）、`get_balance >= point_cost`（否則 4xx insufficient-points 且不扣點），成功回傳兌換結果與 `new_balance`。落實 spec「Student redeems a prize with sufficient points」「Redemption is rejected when the balance is insufficient」「Redemption is restricted to class members」「Redemption is rejected for an invisible or cross-class prize」。驗證：`tests/test_prizes.py` redeem 成功 / 不足 / 非 member / 不可見 / 他班 各案通過。

## 2. 獎品頁路由與 template（前端）

- [x] 2.1 依「學生與教師獎品頁掛在既有 router 的 @webpage.page 路由（不動 main.py）」決策，在 `src/gamification/prizes/router.py` 新增兩個 `@webpage.page` 頁路由：`GET /pages/classes/{class_id}/prizes`（`name="prizes_page"`，render `student/prizes.html`，用 `get_page_user`+`build_page_context`，context 含 visible 獎品清單、學生 `get_balance` 餘額、`class_id`）與 `GET /pages/classes/{class_id}/prizes/manage`（`name="prizes_manage_page"`，render `teacher/prizes_manage.html`，`can_manage_class` 守門、否則 403，context 含該班全部獎品含 `visible`）。落實 spec「Student prize redemption page」與「Teacher prize management HTML page」之路由與守門。驗證：`tests/test_prizes.py` 學生頁回 200 且只列 visible 獎品、教師管理頁對非管理者回 403。
- [x] 2.2 [P] 建立 `src/templates/student/prizes.html`：列出該班 visible 獎品與 `point_cost`、顯示學生目前餘額，每個獎品一顆「兌換」按鈕，按下以 P0 共用 `Modal.confirm` 確認後 `fetch` POST redeem 端點，成功就地更新餘額與該列結果、失敗顯示錯誤；請求進行中按鈕 `disabled`（in-flight 鎖），獎品 `title`/`description` 走 autoescape、就地更新用 `textContent` 不用 `| safe`。落實 spec「Student prize redemption page」之就地更新與 in-flight 行為。驗證：手動於瀏覽器確認兌換後餘額就地下降且按鈕兌換中停用。
- [x] 2.3 [P] 建立 `src/templates/teacher/prizes_manage.html`：重用既有 create/list/patch/delete 端點，提供獎品列表（含 hidden）、建立表單（title/description/point_cost/visible）、切換 visibility、刪除，風格與既有教師頁一致。落實 spec「Teacher prize management HTML page」之列表/建立/切換/刪除。驗證：手動於瀏覽器以教師身分建立獎品後出現在列表，且切換 visibility 與刪除生效。

## 3. 導覽鏈結

- [x] 3.1 依「導覽鏈結加在 dashboard 班級卡片，不改 base.html」決策，在 `src/templates/student/dashboard.html` 既有「排行榜／積分管理」鏈結區塊加教師「獎品管理」連到 `prizes_manage_page`，並在學生班級卡片加「兌換獎品」連到 `prizes_page`，不改動 `src/templates/shared/base.html`。落實兩個獎品頁的入口可達性。驗證：手動於 dashboard 確認教師卡片可進管理頁、學生卡片可進兌換頁。

## 4. 測試

- [x] 4.1 在 `tests/test_prizes.py` 補 redeem 成功與餘額不足測試：成功扣 `point_cost` 且餘額下降、恰新增一筆負額交易；餘額不足回 4xx 且交易數與餘額不變（無扣點）。落實 spec「Student redeems a prize with sufficient points」與「Redemption is rejected when the balance is insufficient」。驗證：`uv run pytest tests/test_prizes.py` 對應測試通過。
- [x] 4.2 在 `tests/test_prizes.py` 補 redeem 守門測試：非 member 學生回 403；不可見獎品與他班（`class_id` 不符）獎品兌換被 4xx 拒絕且無扣點。落實 spec「Redemption is restricted to class members」與「Redemption is rejected for an invisible or cross-class prize」。驗證：`uv run pytest tests/test_prizes.py` 對應測試通過、且各拒絕案後交易數不變。
- [x] 4.3 在 `tests/test_prizes.py` 補 handoff §5 兩項缺漏授權測試：教師 A 帶教師 B 的 `prize_id` 對 `PATCH /prizes/{id}`、`DELETE /prizes/{id}` 跨教師 IDOR 回 403；缺 `MANAGE_TASKS` 權限回 403。落實 spec「Prize mutation endpoints enforce ownership and permission」。驗證：`uv run pytest tests/test_prizes.py` 對應測試通過。
