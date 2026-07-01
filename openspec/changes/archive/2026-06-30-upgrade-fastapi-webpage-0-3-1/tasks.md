## 1. 版本鎖定與升級（lock + sync）

- [x] 1.1 在 `pyproject.toml` 的 `[tool.uv.sources]` 將 `fastapi-webpage` 改為 `{ git = "https://github.com/cxphoenix/fastapi-webpage.git", tag = "v0.3.1" }`，落實設計決策「鎖定 `tag = "v0.3.1"` 取代未鎖 rev 的浮動 git 來源」，達成需求 "SSR rendering library is pinned to a tagged release"。驗證：檔內該行含 `tag = "v0.3.1"` 且不再是未鎖 rev 的浮動 git 來源。
- [x] 1.2 執行設計決策「以 `uv lock --upgrade-package fastapi-webpage` + `uv sync` 升級並同步本地 venv」中的 lock 步驟：`uv lock --upgrade-package fastapi-webpage`，使 `uv.lock` 的 `fastapi-webpage` 由 0.2.1 推進到 0.3.1 並解析新增直接相依 `starlette>=0.40.0`。驗證：`uv.lock` 內 `name = "fastapi-webpage"` 段 `version = "0.3.1"`、git source 指向 v0.3.1 commit，且出現 `starlette` 解析條目。
- [x] 1.3 執行 `uv sync`，把 v0.3.1 裝入本地 `.venv`，讓 pytest 跑在新版上（同屬決策「以 `uv lock --upgrade-package fastapi-webpage` + `uv sync` 升級並同步本地 venv」）。驗證：`uv run python -c "import importlib.metadata as m; print(m.version('fastapi-webpage'))"` 輸出 `0.3.1`。

## 2. 相容性研究固化（v0.3.1 原始碼級，read-only）

- [x] 2.1 [P] 確認設計決策「私有屬性 `webpage._template.env.filters["gravatar_url"]` 相容性確認（#1 break risk）」：v0.3.1 `WebPage` 仍以 `Jinja2Templates` 建立 `_template`，`_template.env.filters` 為可寫 dict，`src/shared/webpage.py` 對 `gravatar_url` 的註冊不報錯，達成需求 "Gravatar Jinja2 filter is registered on the WebPage template environment"。驗證：`uv run python -c "from shared.webpage import webpage; print('gravatar_url' in webpage._template.env.filters)"` 輸出 `True`（於 `src` 為 import root 的環境下）。
- [x] 2.2 [P] 確認設計決策「`@webpage.redirect` 兩種回傳形態 + 新增 scheme 白名單的相容性」：`(str, int)` tuple（`src/pages/router.py:93` 等）與 raw `RedirectResponse`（`src/pages/router.py:97`）兩種回傳皆續受理，且相對 `/...` 路徑原樣保留，達成需求 "Redirect handlers accept both tuple and RedirectResponse return shapes"。驗證：`uv run pytest tests/test_pages.py -q` 中 login/logout 等 redirect 案例通過。
- [x] 2.3 [P] 確認設計決策「`WebPage(...)` 建構子、`@webpage.page`、`webpage_context_update`、`__call__` 的相容性」：建構子簽名不變、29 處 `@webpage.page` 與 4 處 `webpage_context_update`（`src/main.py:79`、`src/core/system/router.py:63` 與 `:123`、`src/pages/router.py:728`）行為不變，達成需求 "Page rendering and global context injection are preserved across the upgrade"。驗證：`uv run pytest tests/test_pages.py tests/test_system_config.py -q` 通過、頁面含注入的 site_name。
- [x] 2.4 [P] 確認設計決策「autoescape 強制啟用對 `| safe` 與 modal 模板的影響評估」：v0.3.1 強制 `env.autoescape = True`，`src/templates/shared/macros.html` 的 `empty_state | safe` 與 modal 模板輸出與升級前相同，達成需求 "Template autoescape remains uniformly enabled"。驗證：`uv run python -c "from shared.webpage import webpage; print(webpage._template.env.autoescape)"` 輸出 `True`。

## 3. 驗證與收斂

- [x] 3.1 對 v0.3.1 跑既有 pytest 全套，確認無 SSR/redirect/context regression。驗證：SSR/redirect/context 相關套件對 v0.3.1 通過——`tests/test_submissions.py`、`tests/test_submission_approval.py` 為 20/20 綠，`tests/test_pages.py`、`tests/test_page_context.py`、`tests/test_gravatar_filter.py` 除下述一筆已知失敗外全綠。已知不相關失敗（out-of-scope，非本升級造成）：`tests/test_pages.py::test_dashboard_teacher_sees_class_data` 拋 `AttributeError: class_id`，根因是該測試的 `init_beanie(document_models=[...])` 未註冊 `JoinRequest`，而 dashboard handler（`src/pages/router.py:211`）執行 `In(JoinRequest.class_id, class_ids)`。此例外在 SSR 渲染前的 beanie query（`func(**kargs)`）即觸發，在 v0.2.1/v0.3.1 下表現完全相同，屬先前 commit（邀請碼加入審核機制）引入的 fixture 缺漏，不在本依賴鎖版變更的 scope 內（test/dashboard 程式碼非本變更可動範圍）。
- [x] 3.2 落實設計決策「app 端零程式碼變更（不修改 webpage.py / call sites）」：確認本變更未改動任何 application code。驗證：`git --no-pager diff --stat -- src/` 為空（僅 `pyproject.toml`、`uv.lock` 有變更）。
- [x] 3.3 收斂分支（預期不觸發）：若 3.1 pytest 或 orchestrator 後續 E2E 出現與 `_template.env`/redirect/context/autoescape 相關失敗，於 `src/shared/webpage.py` 做最小調整使其在 v0.3.1 相容（call site 為最後手段）。驗證：調整後重跑 `uv run pytest` 通過；若未觸發則此任務標記為 N/A 並記錄研究結論成立。

## 4. 交接邊界（非本變更執行）

- [x] 4.1 記錄 image rebuild 與全 live browser E2E（SSR、redirect、SetupGuard、error pages、gravatar 頭像）由 orchestrator 於主迴圈負責——`Dockerfile:52` 以 `uv sync --frozen --no-cache` 於 build 時安裝，故 lock 變更後須重 build 才生效。驗證：proposal/design 已標明此為 out-of-scope，apply 不在本機執行 docker build。
