## Problem

Codex review 在 `achievement-dsl` 合併後發現 5 個問題，其中 1 個 P0 會直接導致打卡/繳交流程崩潰：

1. **[P0] `get_all()` 回傳型別從 list 改為 dict，破壞現有 caller** — `ExtensionRegistry.get_all()` 被改為回傳 `dict[str, Any]`，但 `get_reward_providers()` 的所有 caller（`checkin/router.py`、`submissions/router.py`）仍以 `for provider in get_reward_providers()` 迭代，這會迭代 dict 的 keys（字串），導致 `'str' object has no attribute 'award'` 錯誤，每次打卡/繳交都會 500。

2. **[P1] join-request review 未驗證 class_id 歸屬** — `review_join_request_endpoint` 用 `class_id` 做權限檢查，但 `review_join_request()` service 函數只用 `request_id` 載入 JoinRequest，未檢查 `jr.class_id == class_id`。教師可以透過猜測 request_id 來核准其他班級的加入申請，造成跨班授權繞過。

3. **[P1] `dsl_engine` PyO3 模組未加入 Python 依賴** — `src/gamification/triggers/service.py` 的 `_validate_expression()` 會 `import dsl_engine`，但 `pyproject.toml` 沒有加入這個依賴。在正式環境（`uv sync` / Docker）部署時，每次建立或更新觸發規則都會觸發 `ModuleNotFoundError` 而 500。

4. **[P2] Discord override 欄位未傳遞至 webhook** — assignment 頁面送出 `dc_title_override`、`dc_desc_override`、`dc_footer_override`，但 `ScheduleRuleRequest` 沒有定義這些欄位，Pydantic 靜默丟棄，導致 Discord 排程訊息的自訂覆寫完全無效。

5. **[P2] 核准 join-request 時未檢查重複 membership** — `review_join_request()` 核准後直接 insert `ClassMembership`，若學生已透過其他途徑加入（例如 `batch_invite_students()` 或公開班級直接加入），會建立重複的 membership 記錄，導致成員列表出現重複。

## Root Cause

1. **P0**：`achievement-dsl` change 中修改 `get_all()` 回傳 dict 以配合 `_evaluate_code_triggers()` 的 `.items()` 呼叫，但未更新 `get_reward_providers()` 及其所有 caller。
2. **P1 join-request**：`review_join_request()` service 函數從一開始就沒有做 class_id 範圍驗證。
3. **P1 dsl_engine**：PyO3 wheel 需要透過 `maturin develop` 安裝到 virtualenv，但未在 `pyproject.toml` 或 Dockerfile 中自動化此步驟。
4. **P2 Discord**：`ScheduleRuleRequest` Pydantic model 缺少 override 欄位定義，前端送出的值被 Pydantic 靜默丟棄。
5. **P2 membership**：service 函數未在 insert 前檢查既有 membership。

## Proposed Solution

1. **P0**：在 `get_reward_providers()` 中呼叫 `.values()` 將 dict 轉為值的 list，維持現有 caller 的迭代行為不變。同時修正型別註解為 `list[Any]`。`get_all()` 維持回傳 dict（`_evaluate_code_triggers` 需要 `.items()`）。

2. **P1 join-request**：在 `review_join_request()` 加入 `class_id` 參數，載入 JoinRequest 後驗證 `jr.class_id == class_id`，不符時 raise ValueError。同步更新 router caller 傳入 `class_id`。

3. **P1 dsl_engine**：將 `dsl-engine` 加入 `pyproject.toml` 的主依賴（非 optional），透過 `[tool.uv.sources]` 指向本地 crate 路徑，使 `uv sync` 自動安裝。Dockerfile 中使用 `uv pip install` 而非裸 `pip`，確保 wheel 安裝到 uv 管理的 virtualenv 中。提供 graceful fallback：`_validate_expression()` 在 `ImportError` 時回傳明確錯誤訊息。

4. **P2 Discord**：在 `ScheduleRuleRequest` 加入 `dc_title_override`、`dc_desc_override`、`dc_footer_override` 三個 Optional[str] 欄位，在 `create_schedule_rule` 中將值傳遞給 webhook 呼叫。

5. **P2 membership**：在 `review_join_request()` 核准邏輯中，先查詢是否已存在 `ClassMembership(class_id, user_id)`，若存在則跳過 insert（冪等操作）。

## Non-Goals

- 不重構 `ExtensionRegistry` 的 API 設計（`get_all` 維持回傳 dict）
- 不修改 Discord webhook 的訊息格式或模板系統
- 不修改 join-request 的 UI 流程

## Success Criteria

- 打卡/繳交流程正常執行，不再因 `get_all()` 回傳 dict 而崩潰
- 教師無法透過猜測 request_id 核准其他班級的 join-request
- 在未安裝 `dsl_engine` 的環境中，建立觸發規則時回傳明確錯誤而非 500
- Discord 排程訊息正確帶入 title/description/footer override
- 重複核准 join-request 不會建立重複的 membership 記錄

## Impact

- 受影響程式碼：
  - `src/extensions/deps.py` — `get_reward_providers()` 回傳值修正
  - `src/core/classes/service.py` — `review_join_request()` 加入 class_id 驗證
  - `src/core/classes/router.py` — 傳入 class_id 給 `review_join_request()`
  - `src/gamification/triggers/service.py` — `_validate_expression()` graceful fallback
  - `pyproject.toml` — 加入 dsl-engine 依賴
  - `Dockerfile` — 加入 maturin build 步驟
  - `src/tasks/templates/router.py` — `ScheduleRuleRequest` 加入 Discord override 欄位
  - 測試檔案（新增/修改）
