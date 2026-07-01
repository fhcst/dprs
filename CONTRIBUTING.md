# 貢獻指南

感謝你對 DPRS（Daily Practice Report System，每日練習報告系統）的關注！本文件說明如何設定開發環境、撰寫程式碼與測試，以及提交 Pull Request（合併請求）。

---

## 目錄

- [開發環境設定](#開發環境設定)
- [專案結構](#專案結構)
- [程式碼風格](#程式碼風格)
- [測試](#測試)
- [Rust DSL Engine 開發](#rust-dsl-engine-開發)
- [Commit 規範](#commit-規範)
- [Spectra 工作流程](#spectra-工作流程)
- [Pull Request 流程](#pull-request-流程)

---

## 開發環境設定

### 前置需求

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（套件管理工具）
- MongoDB 8.0（本機或透過 Docker）
- Redis 7（本機或透過 Docker）

### 安裝步驟

```bash
# 複製儲存庫
git clone https://github.com/fhcst/dprs.git
cd dprs

# 安裝相依套件
uv sync

# 僅啟動資料庫服務（不啟動 app 容器）
docker compose up mongo redis -d

# 設定環境變數
export MONGO_URL=mongodb://localhost:27017
export MONGO_DB_NAME=dprs_dev
export REDIS_URL=redis://localhost:6379/0

# 啟動開發伺服器（含熱重載）
uv run fastapi dev src/main.py

# （選用）安裝 Rust toolchain — 僅在修改 DSL 引擎時需要
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup target add wasm32-unknown-unknown
cargo install wasm-pack
```

開發伺服器預設在 `http://localhost:8000` 啟動，首次啟動會自動導向 Setup Wizard（設定精靈）。

---

## 專案結構

```
src/
├── main.py                  # 應用程式進入點、Middleware 註冊、Router 掛載
├── core/                    # 核心模組
│   ├── auth/                # 認證、JWT、Permission（權限）
│   ├── users/               # 使用者 CRUD、CSV 匯入
│   ├── classes/             # 班級管理
│   └── system/              # 系統設定、Setup Wizard
├── tasks/                   # 任務相關
│   ├── templates/           # 任務範本（Task Template）
│   ├── submissions/         # 練習報告提交
│   └── checkin/             # 每日簽到
├── gamification/            # 遊戲化機制
│   ├── points/              # 點數系統
│   ├── badges/              # 徽章系統
│   ├── leaderboard/         # 排行榜
│   └── prizes/              # 獎品預覽
├── community/feed/          # 社群牆
├── extensions/              # Extension Registry（擴充註冊中心）
│   ├── protocols/           # Protocol 定義（AuthProvider、RewardProvider 等）
│   └── registry/            # 註冊中心核心
├── pages/                   # Web UI 頁面路由
├── shared/                  # 共用模組（資料庫、Redis、CSRF、Rate Limiter）
└── templates/               # Jinja2 HTML 模板

crates/dsl-engine/
├── src/                     # Rust 原始碼（parser, validator, evaluator, complete, hover, describe, help）
│   ├── wasm.rs              # WASM binding (wasm-bindgen)
│   └── python.rs            # PyO3 binding
├── dsl.pest                 # PEG grammar 定義
├── pkg/                     # 預建 WASM npm package
└── justfile                 # build 命令封裝
```

每個模組通常包含 `models.py`（Beanie Document 定義）、`router.py`（FastAPI 路由）、`service.py`（商業邏輯）。

詳細架構說明請參閱 [docs/architecture.md](docs/architecture.md)。

---

## 程式碼風格

- **Python**：遵循 PEP 8，行寬上限 120 字元
- **Import 排序**：標準函式庫 → 第三方套件 → 專案模組，各群組間空一行
- **型別標註（Type Annotation）**：公開函式與方法應加上型別標註
- **命名慣例**：
  - 變數與函式：`snake_case`
  - 類別：`PascalCase`
  - 常數：`UPPER_SNAKE_CASE`
  - 私有成員：前綴底線 `_private_method`

---

## 測試

### 測試框架

- [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [mongomock-motor](https://github.com/michaelkryukov/mongomock_motor)：Mock MongoDB，不需實際執行 MongoDB
- [fakeredis](https://github.com/cunla/fakeredis-py)：Mock Redis

### 執行測試

```bash
# 執行全部測試
uv run pytest

# 執行特定測試檔案
uv run pytest tests/test_auth.py -v

# 僅執行符合關鍵字的測試
uv run pytest -k "test_login" -v
```

### 撰寫測試

- 測試檔案放在 `tests/` 目錄下，檔名以 `test_` 為前綴
- 使用 `async def test_*` 撰寫非同步測試（asyncio_mode 已設為 auto）
- 每個測試應獨立，透過 Fixture 建立所需的 Mock 資料庫與使用者
- 涉及 HTTP 端點的測試使用 `httpx.AsyncClient` + `ASGITransport`

範例：

```python
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client.get_database("test_db")
    from core.users.models import User
    await init_beanie(database=database, document_models=[User])
    yield database
    client.close()


async def test_example(db):
    from core.users.models import User
    user = User(username="test", hashed_password="...", display_name="T", permissions=0)
    await user.insert()
    assert await User.count() == 1
```

---

## Rust DSL Engine 開發

若需修改 DSL 引擎（`crates/dsl-engine/`），請先確認已安裝 Rust toolchain（參閱[安裝步驟](#安裝步驟)中的選用項目）。

### WASM Build

```bash
cd crates/dsl-engine && wasm-pack build --target web --out-dir pkg
```

### PyO3 Build

```bash
cd crates/dsl-engine && maturin develop --features python
```

### 測試

```bash
cd crates/dsl-engine && cargo test --lib
```

### justfile 快捷命令

| 命令 | 說明 |
|------|------|
| `just wasm` | 建置 WASM package |
| `just python` | 建置 PyO3 binding |
| `just test` | 執行 Rust 單元測試 |
| `just all` | 執行以上全部步驟 |

> **注意**：修改 Rust 程式碼後需重新 build WASM 和 PyO3 才能在前端/後端看到變更。

---

## Commit 規範

本專案使用 **Emoji + Type** 格式的 Commit Message（提交訊息），以繁體中文撰寫：

```
<Emoji> <type>: <摘要>

## 📋 變更細節分析
- 變更項目 1
- 變更項目 2

## 🔧 技術影響
- 架構或 Breaking Change 說明（若無則省略此區段）
```

### Emoji 與 Type 對照表

| Emoji | Type | 使用時機 |
|-------|------|----------|
| ✨ | `feat` | 新功能 |
| 🐛 | `fix` | Bug 修正 |
| ♻️ | `refactor` | 重構（不改變行為） |
| ⚡️ | `perf` | 效能改善 |
| 📝 | `docs` | 文件變更 |
| 💄 | `style` | 格式調整（不影響邏輯） |
| 🏗️ | `build` | 建置系統或相依套件變更 |
| 🔧 | `chore` | 維護工作（不涉及 src/tests） |

---

## Spectra 工作流程

本專案使用 **Spectra** 進行 Spec-Driven Development（規格驅動開發）。變更提案與規格文件存放在 `openspec/` 目錄。

### 基本流程

```
discuss? → propose → apply ⇄ ingest → archive
```

| 階段 | 說明 | 指令 |
|------|------|------|
| **Discuss** | 需求釐清與討論（可選） | `/spectra:discuss` |
| **Propose** | 建立變更提案與規格文件 | `/spectra:propose` |
| **Apply** | 依據 Tasks 實作程式碼 | `/spectra:apply` |
| **Ingest** | 中途變更需求時更新 Artifacts | `/spectra:ingest` |
| **Archive** | 完成後封存並同步 Spec | `/spectra:archive` |

### 目錄結構

```
openspec/
├── config.yaml              # Spectra 設定（schema、tdd、parallel_tasks 等）
├── specs/                   # 正式規格文件（按 Capability 分類）
│   ├── user-auth/spec.md
│   ├── class-management/spec.md
│   └── ...
└── changes/                 # 進行中的變更提案
    └── <change-name>/
        ├── proposal.md      # 變更提案
        ├── design.md        # 設計決策
        ├── specs/           # Delta Spec（差異規格）
        └── tasks.md         # 實作任務清單
```

---

## Pull Request 流程

1. **建立 Branch（分支）**：從 `staging` 分支建立功能分支

   ```bash
   git checkout staging
   git pull origin staging
   git checkout -b feat/your-feature-name
   ```

2. **實作與測試**：完成程式碼變更並確保測試通過

   ```bash
   uv run pytest
   ```

3. **提交**：依照 [Commit 規範](#commit-規範) 撰寫提交訊息

4. **推送與建立 PR**：

   ```bash
   git push -u origin feat/your-feature-name
   gh pr create --base staging
   ```

5. **PR 說明**：在 PR 描述中包含：
   - 變更摘要
   - 相關的 Spectra Change（若有）
   - 測試計畫

6. **Review（審閱）**：等待 Maintainer 審閱，依回饋修正後合併

---

## 相關文件

- [系統架構](docs/architecture.md)
- [環境設定](docs/configuration.md)
- [Extension 開發指南](docs/extensions.md)
- [Migration 系統](docs/migrations.md)
- [安全政策](SECURITY.md)
