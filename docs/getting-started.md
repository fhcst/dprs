# 快速入門

本文件說明如何安裝並啟動 DPRS（Daily Practice Report System，每日練習報告系統）。

---

## 前置需求

依據你的部署方式，需要準備以下工具：

| 方式 | 需求 |
|---|---|
| Docker 部署（推薦） | [Docker](https://docs.docker.com/get-docker/) 含 Docker Compose（Docker Compose 為 Docker Desktop 內建） |
| 本機開發 | Python 3.13 以上、[uv](https://docs.astral.sh/uv/)（Python 套件管理工具）、MongoDB 8.0、Redis 7 |

### 選用：Rust toolchain

> **僅在修改 `crates/dsl-engine/` 原始碼時需要，不安裝 Rust 不影響專案啟動和使用。**
> 若未安裝 Rust，觸發規則功能會顯示明確錯誤提示。

安裝指令：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

---

## 使用 Docker Compose 部署

### 1. 複製環境變數檔

```bash
cp .env.example .env
```

### 2. 設定必要環境變數

以文字編輯器開啟 `.env`，設定以下必要的環境變數（Environment Variables）：

```dotenv
# 應用程式 Session 加密金鑰 — 請使用高強度隨機字串
SESSION_SECRET=<替換為你的密鑰>

# MongoDB 管理者密碼
MONGO_ROOT_PASSWORD=<替換為你的密碼>

# Redis 密碼
REDIS_PASSWORD=<替換為你的密碼>
```

> **提示：** 可用 `openssl rand -hex 32` 產生安全的隨機字串。

其餘選填變數及其預設值：

| 變數 | 說明 | 預設值 |
|---|---|---|
| `FASTAPI_APP_ENVIRONMENT` | 執行環境，`dev` 或 `prod` | `dev` |
| `MONGO_ROOT_USERNAME` | MongoDB 管理者帳號 | `admin` |
| `MONGO_DB_NAME` | MongoDB 資料庫（Database）名稱 | `dts2` |

### 3. 啟動服務

```bash
docker compose up -d
```

首次執行時，Docker 會自動建置應用程式映像檔（Image）並下載 MongoDB、Redis 映像檔，需等待數分鐘。

### 4. 服務連接埠

啟動完成後，各服務對應的連接埠（Port）如下：

| 服務 | 連接埠 | 說明 |
|---|---|---|
| DPRS 應用程式 | `8000` | 主要 Web 介面 |
| MongoDB | `27017`（僅 localhost） | 資料庫，僅限本機存取 |
| Redis | `6379`（僅 localhost） | 快取與 Session 儲存，僅限本機存取 |
| Mongo Express | `8081` | 資料庫管理介面（需啟用 `debug` Profile） |

> **注意：** Mongo Express 未包含在預設啟動範圍內。如需啟用，請執行：
>
> ```bash
> docker compose --profile debug up -d
> ```

---

## 本機開發環境設定

適合需要修改程式碼的開發者。

### 1. 安裝相依套件（Dependencies）

```bash
uv sync
```

此指令會依據 `pyproject.toml` 與 `uv.lock` 安裝所有相依套件。

### 2. 啟動 MongoDB 與 Redis

你可以選擇在本機安裝 MongoDB 和 Redis，或僅透過 Docker Compose 啟動這兩項服務：

```bash
docker compose up -d mongo redis
```

### 3. 設定環境變數

```bash
export SESSION_SECRET=$(openssl rand -hex 32)
export MONGO_URL=mongodb://admin:<你的密碼>@localhost:27017
export MONGO_DB_NAME=dts2
export REDIS_URL=redis://:<你的密碼>@localhost:6379/0
```

或者將上述變數寫入 `.env` 檔案，應用程式亦會自動讀取。

### 4. 啟動開發伺服器（Development Server）

```bash
uv run fastapi dev src/main.py
```

開發伺服器預設監聽 `http://127.0.0.1:8000`，並支援程式碼熱重載（Hot Reload）——修改 `src/` 底下的檔案後，伺服器會自動重新載入。

### 5. DSL 引擎建置（選用）

安裝 PyO3 binding，讓後端可以呼叫 Rust DSL 引擎：

```bash
# 安裝 PyO3 binding（讓後端可以呼叫 Rust DSL 引擎）
cd crates/dsl-engine
maturin develop --features python
cd ../..
```

> **不執行此步驟不影響其他功能。** 建立觸發規則時會收到「DSL engine is not installed」錯誤，但其他所有功能正常運作。

若需修改 WASM（前端 DSL 編輯器）：

```bash
wasm-pack build --target web --out-dir pkg
```

---

## 首次啟動

系統首次啟動時，資料庫中尚未建立任何設定，所有請求都會被自動導向至 `/setup` 初始化精靈（Setup Wizard）。

在 Setup Wizard 中，你需要完成以下設定：

1. **站台名稱（Site Name）** — 顯示於系統介面上方的名稱
2. **管理者帳號（Admin Username）** — 系統最高權限管理者的登入帳號
3. **管理者密碼（Admin Password）** — 至少 8 個字元

完成後即可以管理者帳號登入系統。

---

## 驗證安裝

啟動服務後，依下列步驟確認系統正常運作：

1. **開啟瀏覽器**，前往 `http://localhost:8000`。
   - 首次啟動應自動導向至 `/setup`。
   - 若已完成初始化設定，則應看到登入頁面。

2. **檢查服務健康狀態**（適用於 Docker Compose 部署）：

   ```bash
   docker compose ps
   ```

   確認 `app`、`mongo`、`redis` 三個服務的狀態（Status）皆顯示 `Up` 且 Health 為 `healthy`。

3. **檢查應用程式 API**：

   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
   ```

   預期回傳 HTTP 狀態碼 `302`（重新導向至登入頁面或 Setup Wizard）。

---

## 下一步

- [configuration.md](configuration.md) — 系統進階設定說明
- [user-guide/admin-setup.md](user-guide/admin-setup.md) — 管理者初始設定指南
