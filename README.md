# Daily Practice Report System (DPRS)

> **版本 0.5.0** — 適用於教學場域的每日練習報告管理平台

教師建立班級、指派每日任務、審閱學生提交，並透過遊戲化機制——點數、徽章與排行榜——提升學生學習動力。學生每日簽到、提交練習報告，並在社群牆上分享學習進度。

---

## 功能特色

### 核心功能

- **認證與授權** — JWT Cookie 認證、Permission IntFlag 權限系統、Role Preset（角色預設）
- **班級管理** — 建立班級、邀請碼加入、公開 / 私有班級、班級封存
- **任務範本（Task Template）** — 自訂欄位的可重複使用範本；依日期指派或排程規則自動指派
- **練習報告提交** — 學生提交後教師審閱（核准 / 退回 / 補繳）；提交時快照範本版本
- **每日簽到（Check-in）** — 可設定簽到時間區間與有效星期，支援單日覆蓋設定

### 遊戲化

- **點數系統** — 簽到與提交事件自動觸發點數獎勵，可依班級設定點數值
- **徽章** — 教師自訂徽章定義，搭配可擴充的觸發條件
- **DSL 觸發規則** — 教師可用表達式語言（如 `checkin_streak >= 7 AND submission_count >= 3`）自訂成就觸發條件；CodeMirror 6 編輯器提供即時語法驗證、自動補全與 hover 提示；前端 dry-run 測試讓教師預覽規則效果；Milkdown WYSIWYG Markdown 編輯器用於徽章說明；DSL Help Modal 提供完整語法參考
- **排行榜** — 以班級為範圍，依累積點數排名；支援跨班級排行
- **獎品預覽** — 顯示與點數里程碑對應的獎品

### 其他

- **社群牆** — 貼文與 Emoji Reaction 互動
- **出席管理** — 遲到 / 缺席標記與補點
- **Discord Webhook** — 任務指派時自動通知
- **Extension Registry（擴充註冊中心）** — 支援 AuthProvider、RewardProvider 等 Protocol 的套件架構
- **Setup Wizard（設定精靈）** — 首次部署自動導向系統初始設定

---

## 技術堆疊

| 層次 | 技術 |
|------|------|
| Runtime | Python 3.13+ |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ODM | [Beanie](https://beanie-odm.dev/)（非同步 MongoDB ODM） |
| Database | MongoDB 8.0 + Redis 7 |
| 套件管理 | [uv](https://github.com/astral-sh/uv) |
| 測試 | pytest + pytest-asyncio + mongomock-motor |
| 容器化 | Docker + Docker Compose |
| **DSL 引擎** | |
| 表達式解析 | [Rust](https://www.rust-lang.org/)（[pest](https://pest.rs/) PEG parser） |
| 前端驗證 | [WebAssembly](https://webassembly.org/)（wasm-pack 編譯） |
| Python 綁定 | [PyO3](https://pyo3.rs/)（[maturin](https://github.com/PyO3/maturin) 建置 FFI） |

---

## 快速開始

### 前置需求

- [Docker](https://docs.docker.com/get-docker/) 與 Docker Compose
- 或：Python 3.13+ 與 [uv](https://github.com/astral-sh/uv)（本機開發）

### 使用 Docker Compose 部署

```bash
cp .env.example .env
# 編輯 .env，設定以下必要變數：
#   SESSION_SECRET=<隨機 32 字元以上的字串>
#   MONGO_ROOT_PASSWORD=<MongoDB 密碼>
#   REDIS_PASSWORD=<Redis 密碼>

docker compose up
```

服務對應埠號：

| 服務 | URL | 說明 |
|------|-----|------|
| 應用程式 | http://localhost:8000 | FastAPI 主服務 |
| Mongo Express | http://localhost:8081 | 需以 `docker compose --profile debug up` 啟動 |

### 本機開發

```bash
uv sync                                  # 安裝相依套件
docker compose up mongo redis -d         # 僅啟動資料庫服務
uv run fastapi dev src/main.py           # 啟動開發伺服器（含熱重載）
```

首次啟動會自動導向 **Setup Wizard**，完成系統名稱與管理員帳號設定。

> **Rust 工具鏈為選裝（OPTIONAL）**
> - 不安裝 Rust 仍可正常執行所有功能。
> - 觸發規則管理功能在未安裝 `dsl_engine` 時會顯示明確錯誤訊息。
> - 若需修改 DSL 引擎原始碼，請安裝 Rust：`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`

> 完整部署說明請參閱 [docs/getting-started.md](docs/getting-started.md)

---

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `FASTAPI_APP_ENVIRONMENT` | `dev` | 設為 `production` 啟用 Cookie Secure、JWT 強制檢查 |
| `SESSION_SECRET` | 自動產生 | JWT 簽名金鑰；**生產環境必須明確設定** |
| `MONGO_URL` | `mongodb://...@mongo:27017` | MongoDB 連線字串（含認證） |
| `MONGO_DB_NAME` | `dts2` | 資料庫名稱 |
| `MONGO_ROOT_PASSWORD` | — | MongoDB Root 密碼；**生產環境必填** |
| `REDIS_PASSWORD` | — | Redis 認證密碼；**生產環境必填** |

> 完整環境變數說明請參閱 [docs/configuration.md](docs/configuration.md)

---

## 文件索引

### 使用者文件

| 文件 | 說明 |
|------|------|
| [docs/getting-started.md](docs/getting-started.md) | 首次部署與啟動 |
| [docs/configuration.md](docs/configuration.md) | 環境變數與設定完整說明 |
| [docs/user-guide/admin-setup.md](docs/user-guide/admin-setup.md) | 系統管理員設定指南 |
| [docs/user-guide/teacher-workflow.md](docs/user-guide/teacher-workflow.md) | 教師操作流程 |
| [docs/user-guide/student-workflow.md](docs/user-guide/student-workflow.md) | 學生操作流程 |

### 開發者文件

| 文件 | 說明 |
|------|------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | 貢獻指南 |
| [docs/architecture.md](docs/architecture.md) | 系統架構與模組設計 |
| [docs/extensions.md](docs/extensions.md) | Extension 擴充套件開發指南 |
| [docs/migrations.md](docs/migrations.md) | 資料庫 Migration 系統 |

### 專案管理

| 文件 | 說明 |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | 版本紀錄 |
| [SECURITY.md](SECURITY.md) | 安全政策與漏洞通報 |

---

## 貢獻

歡迎提交 Pull Request！詳細流程請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 安全性

發現安全漏洞請**勿**公開提交 Issue，請參閱 [SECURITY.md](SECURITY.md) 的通報流程。

## 授權

[ECL-2.0](LICENSE)
