## 1. [P0] ExtensionRegistry get_all() 回傳值修正

- [x] 1.1 修改 `src/extensions/deps.py` 的 `get_reward_providers()` 函數：呼叫 `registry.get_all(RewardProvider).values()` 並轉為 `list`，確保回傳 `list[Any]` 而非 `dict`。同步修正 `get_submission_validators()` 若有相同問題 — 對應 Requirement「FastAPI dependency injection via registry」中 Reward providers iterated as list 場景
- [x] [P] 1.2 撰寫測試驗證 `get_reward_providers()` 回傳 list 且元素為 RewardProvider 實作物件（非字串 key），在 `tests/test_extensions.py` 中新增測試案例

## 2. [P1] join-request 跨班授權修正

- [x] 2.1 修改 `src/core/classes/service.py` 的 `review_join_request()` 函數：新增 `class_id: str` 參數，載入 JoinRequest 後驗證 `jr.class_id == class_id`，不符時 raise `ValueError("Join request does not belong to the specified class")` — 對應 Requirement「Teacher reviews join request」中跨班驗證場景
- [x] 2.2 修改 `src/core/classes/router.py` 的 `review_join_request_endpoint()`：傳入 `class_id` 給 `review_join_request(request_id=request_id, class_id=class_id, action=body.action, reviewer=user)` — 對應 Requirement「Teacher reviews join request」
- [x] [P] 2.3 在 `review_join_request()` 核准邏輯中，insert `ClassMembership` 前先查詢 `await ClassMembership.find_one(ClassMembership.class_id == jr.class_id, ClassMembership.user_id == jr.user_id)`，若已存在則跳過 insert — 對應 Requirement「Student joins a class」（冪等 membership 建立）
- [x] [P] 2.4 撰寫測試：(a) 跨班 request_id 被拒絕、(b) 正常班級核准成功、(c) 重複核准不會建立重複 membership — 在 `tests/test_class_permissions.py` 或新檔中新增

## 3. [P1] dsl_engine 模組安裝與 graceful fallback

- [x] 3.1 修改 `src/gamification/triggers/service.py` 的 `_validate_expression()` 函數：將 `import dsl_engine` 包在 try/except ImportError 中，ImportError 時 raise `ValueError("DSL engine (dsl_engine) is not installed. Please run 'maturin develop --features python' in crates/dsl-engine/")` — 對應 Requirement「Graceful error when dsl_engine not installed」場景
- [x] [P] 3.2 在 `pyproject.toml` 的依賴或文件中記錄 dsl-engine 的安裝步驟（`[project.optional-dependencies]` 或 README），確保開發者知道需要執行 `maturin develop` — 對應 Requirement「Dual compilation targets」中 PyO3 wheel importable 場景
- [x] [P] 3.3 更新 `Dockerfile`：在 Python 依賴安裝之後加入 `RUN pip install maturin && cd crates/dsl-engine && maturin build --features python --release --out /tmp/wheels && pip install /tmp/wheels/*.whl` 步驟

## 4. [P2] Discord override 欄位傳遞

- [x] 4.1 修改 `src/tasks/templates/router.py` 的 `ScheduleRuleRequest` Pydantic model：新增 `dc_title_override: Optional[str] = None`、`dc_desc_override: Optional[str] = None`、`dc_footer_override: Optional[str] = None` 三個欄位 — 對應 Requirement「Task assignment supports per-task template overrides」
- [x] 4.2 修改 `create_schedule_rule` 端點：將 `body.dc_title_override`、`body.dc_desc_override`、`body.dc_footer_override` 傳遞給 Discord webhook 呼叫（具體傳遞方式需查看現有 webhook 呼叫位置，可能在 TaskScheduleRule model 中儲存或直接傳給 webhook sender）— 對應 Requirement「Schedule rule created with Discord overrides」場景

## 5. 迴歸測試驗證

- [x] [P] 5.1 執行完整測試套件 `uv run python -m pytest tests/` 確保所有既有測試通過（特別是 `test_badges.py`、`test_extensions.py`、`test_checkin.py`、`test_submissions.py`）
- [x] [P] 5.2 手動驗證 `for provider in get_reward_providers(): await provider.award(event)` 路徑在打卡/繳交時不會觸發 AttributeError

## 6. [P1] Codex Review Round 2 — dsl_engine 安裝路徑修正

- [x] 6.1 修改 `pyproject.toml`：將 `dsl-engine` 從 `[project.optional-dependencies]` 移至主 `dependencies` 列表，確保 `uv sync` 自動安裝。`[tool.uv.sources]` 中的 `dsl-engine = { path = "crates/dsl-engine", editable = true }` 保留不動 — 對應 Requirement「Dual compilation targets」中 PyO3 wheel importable 場景；修正 Codex Review Round 2 P2（plain `uv sync` 不安裝 optional dep）
- [x] 6.2 修改 `Dockerfile`：將 `pip install maturin` 和 `pip install /tmp/wheels/*.whl` 替換為 `uv pip install`，確保 wheel 安裝到 uv 管理的 `.venv` 而非系統 Python。具體做法：`uv pip install maturin` → `cd crates/dsl-engine && maturin build --features python --release --out /tmp/wheels` → `uv pip install /tmp/wheels/*.whl` — 對應 Codex Review Round 2 P1（wheel 安裝到錯誤的 interpreter）

## 7. 第二輪迴歸測試

- [x] [P] 7.1 執行完整測試套件確認所有測試通過
