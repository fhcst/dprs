## Context

`fastapi-webpage` 是本專案 SSR 的核心相依。問題現況：

- `pyproject.toml:34` 的 git 來源未鎖 rev（floating）。
- `uv.lock`（行 386-388）把版本釘在 `version = "0.2.1"` / `source = { git = "...#09d434f9324c8a8c1b21696f57d312f45d8a2d33" }`。
- `Dockerfile:52` 以 `uv sync --frozen --no-cache` 於 build 時安裝，因此 container 永遠是 lock 中的 0.2.1。
- upstream 現況：`git ls-remote` → `refs/tags/v0.3.1` = `49145d18a81c4247698a29b10104ff8bdf7fcd05`（中間另有 v0.3.0）。

升級必經風險：v0.2.x → v0.3.x 為 pre-1.0 minor bump。本設計以 upstream 原始碼（clone 至 scratchpad，逐 tag diff）完成相容性研究，作為「是否需動 app 程式碼」的依據。

研究方法：`git diff v0.2.1 v0.3.1` 比對 `fastapi_webpage/{webpage.py,__init__.py,error_middleware.py}` 與 `pyproject.toml`、`CHANGELOG.md`，再對照 app 端實際 call sites（`grep` 出 29 處 `@webpage.page`、10 處 `@webpage.redirect`、4 處 `webpage_context_update`、1 處私有屬性存取）。

## Goals / Non-Goals

**Goals:**

- 把 `fastapi-webpage` 明確鎖到 `tag = "v0.3.1"`，終結浮動 git 來源。
- 讓 `uv.lock` 與本地 `.venv` 同步到 v0.3.1，使 pytest 跑在新版上。
- 以原始碼級相容性研究確認 app 實際使用的 surface 在 v0.3.1 不 break，並把結論固化成 `webpage-rendering` capability 的 spec。

**Non-Goals:**

- 不做 image rebuild、不跑 live browser E2E（由 orchestrator 於主迴圈另行處理）。
- 不修 E2E 報告中的 BUG-1/BUG-2/BUG-4/BUG-5（屬其他 handoff）。
- 不重構 `src/shared/webpage.py` 的私有屬性存取寫法（即使其為 pre-1.0 私有 API；只要 v0.3.1 仍相容就維持現狀，避免把升級與重構混在一起）。

## Decisions

### 鎖定 `tag = "v0.3.1"` 取代未鎖 rev 的浮動 git 來源

把 `[tool.uv.sources]` 的 `fastapi-webpage = { git = "..." }` 改為 `{ git = "...", tag = "v0.3.1" }`。

- 為何用 `tag` 而非 `rev`：tag `v0.3.1` 指向 commit `49145d1`（已用 `git rev-parse v0.3.1^{commit}` 驗證），語意清楚、與 CHANGELOG 對得起來；uv 會把實際 commit 寫進 `uv.lock`，可重現性等同 rev。
- 替代方案（rev = `49145d1`）：可行但可讀性差、與 release note 對應需額外查表，故捨棄。
- 政策：日後一律鎖 tag，避免再次無聲落後。

### 以 `uv lock --upgrade-package fastapi-webpage` + `uv sync` 升級並同步本地 venv

只升 `fastapi-webpage` 單一套件，避免順帶更動其他相依。`uv lock --upgrade-package` 會把 lock 內版本由 0.2.1 推到 0.3.1，並依 v0.3.1 `pyproject.toml` 新增的直接相依 `starlette>=0.40.0` 重新解析；接著 `uv sync` 把新版裝進 `.venv`，讓既有 pytest 套件直接對新版執行。

### 私有屬性 `webpage._template.env.filters["gravatar_url"]` 相容性確認（#1 break risk）

這是 handoff 標記最該 de-risk 的一項。研究結論：**維持不變、可安全保留**。

- v0.3.1 `WebPage.__init__` 仍為 `self._template = Jinja2Templates(template_directory)`，緊接著 `self._template.env.globals["url_for"] = urlx_for`（lib 自己就是用同一條 `_template.env.<dict>` 路徑註冊全域），新增的唯一一行是 `self._template.env.autoescape = True`。
- 因此 `webpage._template` 屬性名、`_template.env`（標準 Jinja2 `Environment`）、以及 `env.filters`（標準 dict）在 v0.3.1 完全存在；app 在 `src/shared/webpage.py` 第 10 行對 `env.filters["gravatar_url"]` 的賦值不受影響，`gravatar_url` filter 仍正常註冊。
- `grep` 確認 app 對 webpage singleton 的私有屬性存取**只有這一處**（其餘 `_template` 命中皆為 app 自身的 TaskTemplate 等網域字眼，非 lib 內部）。

### `@webpage.redirect` 兩種回傳形態 + 新增 scheme 白名單的相容性

研究結論：**三種回傳形態皆續受理；新增的安全檢查對 app 既有目標零影響**。

- v0.3.1 redirect handler 的 `match` 仍涵蓋 `RedirectResponse()`、`Response()`、`str()`、`(str() as url, int() as code)` 四個 case。app 端實際用到其中三種回傳形態，皆對應到既有 case：
  - `(str, int)` tuple（如 `src/pages/router.py:93`、`src/tasks/checkin/router.py:146` 與 `:150`）。
  - raw `RedirectResponse`（如 `src/pages/router.py:97`）。
  - bare URL string（`src/core/system/router.py:130` 的 `return "/"`、`src/tasks/checkin/router.py:155` 的 `return str(request.url_for("dashboard_page"))`）——對應 v0.3.1 `webpage.py` 的 `case str():` 分支，會以 `_adjust_scheme` 調整 scheme 後，用 decorator 宣告的 `status_code`（這兩處皆為 302）建立 `RedirectResponse`，與 v0.2.1 行為一致。
- v0.3.1 把 `_adjust_scheme` 提到 module level 並加上 scheme 白名單（`http`/`https`/`ws`/`wss`）：對「無 netloc 但帶非白名單 scheme」（`javascript:`/`data:`/`mailto:`…）回 500。app 的 redirect 目標一律是相對 `/...` 路徑（無 scheme 無 netloc → 原樣保留）或 `request.url_for(...)` 產生的 http/https 絕對 URL（有 netloc → 走既有 scheme 調整），皆不觸發新 500；`grep` 確認 app redirect/url 情境無任何危險 scheme 字面值。此檢查屬安全強化，對本 app 為淨正向。

### `WebPage(...)` 建構子、`@webpage.page`、`webpage_context_update`、`__call__` 的相容性

- 建構子 `WebPage(template_directory=...)` 簽名未變。
- `@webpage.page`（app 29 處）裝飾器對外 API 未變；內部 `TemplateResponse` 由舊式改為 `request=`-first 現代簽名（v0.3.0 變更），對使用者 API 無影響，`match` 各 case 不變。
- `webpage_context_update(self, value: dict)`（app 4 處：`src/main.py:79`、`src/core/system/router.py:63` 與 `:123`、`src/pages/router.py:728`）在 v0.3.1 仍存在、簽名不變。
- `__call__` 把可變預設 `context={}` 改為 `context: dict | None = None` 並於內部複製：app **未**直接呼叫 `webpage(...)`（`grep` 為 none），即使呼叫此變更也只會更安全（不再汙染呼叫者 dict）。

### autoescape 強制啟用對 `| safe` 與 modal 模板的影響評估

研究結論：**無行為變化、與 BUG-1 無交互風險**。v0.3.0+ 在 `__init__` 強制 `env.autoescape = True`（不分副檔名），與 v0.2.1 在 Starlette 0.50.x 下的 effective「一律啟用」一致。app 模板既有 `| safe` 用法（目前僅 `src/templates/shared/macros.html` 的 `empty_state` macro，且其 icon 為模板內寫死的靜態 SVG）在升級前後輸出完全相同；modal 模板的轉義行為亦不變。

### app 端零程式碼變更（不修改 webpage.py / call sites）

綜合上述，v0.3.1 對 app 實際使用的 surface 完全向下相容，因此**本變更不修改 `src/shared/webpage.py` 也不修改任何 call site**。僅當後續驗證推翻此結論時，才在 `src/shared/webpage.py` 內做最小調整、call site 為最後手段。

## Implementation Contract

- **行為（不變）**：升級後 app 啟動、SSR 頁面渲染、redirect、context 注入、gravatar 頭像 filter 行為與 v0.2.1 完全一致，無 regression。
- **介面 / 資料形狀**：
  - `pyproject.toml` `[tool.uv.sources]`：`fastapi-webpage = { git = "https://github.com/cxphoenix/fastapi-webpage.git", tag = "v0.3.1" }`。
  - `uv.lock`：`fastapi-webpage` 段 `version` 由 `0.2.1` 變為 `0.3.1`，`source` 的 git fragment 由 `#09d434f...` 變為 v0.3.1 對應 commit；並出現直接相依 `starlette`（>=0.40.0 解析結果）。
  - `.venv`：`uv pip show fastapi-webpage`（或 `uv run python -c "import fastapi_webpage, ...; print(version)"`）顯示 0.3.1。
- **驗收標準**：
  1. `pyproject.toml` 已鎖 `tag = "v0.3.1"`；`uv.lock` 內 `fastapi-webpage` 為 0.3.1。
  2. `uv sync` 後本地 `.venv` 安裝 0.3.1。
  3. 既有 pytest 全套對 v0.3.1 通過：`uv run pytest`（特別關注 `tests/test_pages.py`、`tests/test_submissions.py`、`tests/test_submission_approval.py` 等觸及 SSR/redirect 的測試）。
  4. `src/shared/webpage.py` 與 call sites 無 diff（驗證「零程式碼變更」結論成立）。
- **失敗模式**：若 `uv sync` 後 import error、或 pytest 出現與 `_template.env`/redirect/context 相關的失敗，代表相容性結論被推翻 → 進入「最小調整 `src/shared/webpage.py`」分支並記錄於 tasks。
- **Scope 邊界**：
  - In scope：`pyproject.toml`、`uv.lock`、本地 `.venv` 同步、相容性研究固化成 spec、pytest 驗證。
  - Out of scope：image rebuild、live browser E2E（orchestrator 主迴圈負責）；E2E 報告其他 BUG 修復；私有屬性存取寫法重構。

## Risks / Trade-offs

- [pre-1.0 minor bump 仍可能有未被 diff 涵蓋的隱性行為差異] → 緩解：以既有 pytest 全套對 v0.3.1 跑一次作為第一道關卡，並由 orchestrator 的 live E2E（SSR/redirect/SetupGuard/error pages/gravatar 頭像）作第二道關卡。
- [繼續依賴 pre-1.0 私有屬性 `_template.env.filters`] → 緩解：本次已逐行確認 v0.3.1 仍相容；風險登記於 spec，未來 lib 若提供公開 filter 註冊 API 再行重構（非本變更範圍）。
- [新增直接相依 `starlette` 可能與 `fastapi[standard]` 既有解析版本相衝] → 緩解：以 `uv lock --upgrade-package fastapi-webpage`（僅升單一套件）讓 uv 統一解析；若解析失敗，lock 步驟即會明確報錯而非無聲降級。
- [image 與本地 venv 暫時版本不一致] → 緩解：本變更只負責 lock + 本地 venv；明確標記 image rebuild 為 orchestrator 後續步驟，避免誤判為遺漏。
