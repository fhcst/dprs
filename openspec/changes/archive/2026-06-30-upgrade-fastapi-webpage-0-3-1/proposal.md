## Why

`fastapi-webpage` 是本專案 SSR 的核心（`@webpage.page`、`@webpage.redirect`、context 注入、以及在 `_template.env` 上註冊的 `gravatar_url` filter）。目前 `pyproject.toml:34` 的 git 來源**未鎖 rev**，`uv.lock` 卻釘在舊 commit `09d434f`（**v0.2.1**），導致 container 以 `uv sync --frozen` build 出來永遠是落後 **2 個 minor** 的版本。upstream 現況為 **v0.3.1**（`49145d1`），其中 v0.3.0 全面相容 Starlette 1.x、v0.3.1 強化 redirect scheme 安全檢查並修掉 `__call__` 可變預設參數 footgun。這是一個維護性（maintenance / refactor）升級：本變更要把版本**明確鎖到 tag**、終結浮動來源，並以相容性研究確認升級對 app 零行為衝擊。

## What Changes

- **鎖定版本**：`pyproject.toml` 的 `[tool.uv.sources]` 將 `fastapi-webpage` 改為 `{ git = "...", tag = "v0.3.1" }`，終結未鎖 rev 的浮動 git 來源。
- **更新 lock 並同步本地 venv**：執行 `uv lock --upgrade-package fastapi-webpage`（uv.lock 由 0.2.1 → 0.3.1，並新增直接相依 `starlette>=0.40.0`），再 `uv sync` 把 v0.3.1 裝入本地 `.venv`，讓 pytest 跑在新版上。
- **相容性研究（本變更核心）**：以 upstream 原始碼逐點比對 app 實際使用的 surface（見下方 Impact 與 design.md）。研究結論為 **app 端零程式碼變更**——`WebPage(...)`、私有屬性 `webpage._template.env.filters["gravatar_url"]`、`@webpage.page`（29 處）、`@webpage.redirect`（10 處，含 `(str,int)` tuple 與 raw `RedirectResponse` 兩種回傳形態）、`webpage.webpage_context_update(...)`（4 處）在 v0.3.1 皆維持相容。
- **無需修改 `src/shared/webpage.py` 或任何 call site**：相容性研究若推翻此結論，才在 `src/shared/webpage.py` 內做最小調整（且僅在真正無法避免時才動 call site）；以目前研究結果，本變更**不寫任何 application code**。
- 非本變更執行範圍：image rebuild 與全 live browser E2E 由 orchestrator 於主迴圈另行處理（lib 在 build 時透過 `uv sync --frozen` 安裝、未掛載，改 lock 後需重 build 才生效）。

## Capabilities

### New Capabilities

- `webpage-rendering`: 規範 SSR 渲染引擎（`fastapi-webpage`）的版本鎖定政策、`gravatar_url` Jinja2 filter 在 WebPage template environment 上的註冊、以及 `@webpage.page` / `@webpage.redirect` / context 注入在升級後須維持的相容性契約（含 autoescape 一律啟用、redirect 回傳兩種形態皆受理）。

### Modified Capabilities

<!-- 無：本變更為行為保留型的相依升級，不更動任何既有 capability 的需求行為。 -->

## Impact

- **相依**：`fastapi-webpage` v0.2.1 → v0.3.1；新增直接相依 `starlette>=0.40.0`（由 lib 帶入，uv 解析）。
- **檔案**：`pyproject.toml`（鎖 tag）、`uv.lock`（重新解析）。**不**修改 `src/shared/webpage.py` 與 call sites（研究結論為相容）。
- **建置／部署**：`Dockerfile:52` `uv sync --frozen --no-cache` 於 build 時安裝，因此 lock 變更後 image 需重 build——由 orchestrator 負責，非本變更範圍。
- **行為**：v0.3.1 強制 `env.autoescape = True`（與 v0.2.1 effective ON 一致），不影響 `empty_state | safe` 與 modal 模板；新增的 redirect scheme 白名單（拒絕 `javascript:`/`data:` 等無 netloc 危險 scheme）對 app 既有 redirect 目標（一律為相對 `/...` 路徑或 `url_for` 產生的 http/https 絕對 URL）零影響，且屬安全強化。
