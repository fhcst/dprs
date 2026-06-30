## Why

專案目前已有可建置的 Dockerfile、`scripts/docker-build.sh`（手動 multi-arch build + push 至 GHCR）與本機用的 `docker-compose.yml`，但缺乏「正式上線」所需的最後一哩：對外服務目前只能靠 host port 8000 直接曝露、沒有任何 MongoDB 備份機制、且 `docker compose up` 預設仍走本機 `build: .`（換機部署得在每台機器重編 Rust/WASM）。本次變更把部署流程 productionize：以 Cloudflare Tunnel 作為唯一對外入口、加入可重複執行的 MongoDB 備份、並把 GHCR 預建映像（image）設為預設執行路徑。

## What Changes

- **Cloudflare Tunnel 對外入口（profile `tunnel`）**
  - 新增 `cloudflared` service（`cloudflare/cloudflared:latest`、`tunnel --no-autoupdate run`、token-based remotely-managed tunnel），ingress route 於 Cloudflare dashboard 設定指向 `http://app:8000`，repo 內不需 `config.yml`/credentials。
  - **BREAKING**（部署層面）：移除 app 預設的 `8000:8000` host publish，改由 compose network 內 `app:8000` 觸達；tunnel 模式對外只剩 Cloudflare 一條路徑。本機 dev 另以**不自動合併**的 `docker-compose.dev.yml`（顯式 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`）重新 publish `127.0.0.1:8000`、並覆寫 `FASTAPI_APP_ENVIRONMENT=dev`；因該檔不自動合併，正式機 `docker compose --profile tunnel up` 結構上即不曝露 host port。
  - 新增 `TUNNEL_TOKEN`〔必填，tunnel profile〕、`TUNNEL_TRANSPORT_PROTOCOL`〔選填，預設 auto〕至 `.env.example`（僅 placeholder，不含真實 token）。
  - 為 app 設定 `FORWARDED_ALLOW_IPS`，使其信任 cloudflared 的 `X-Forwarded-Proto: https`，讓 Secure cookie 與 scheme 偵測能在 tunnel 後端正確運作。

- **MongoDB 備份**
  - 新增 `scripts/backup.sh`：以 compose 的 mongo 認證執行 `mongodump`，輸出帶時間戳的壓縮檔至 host-mounted `./backups/`，idempotent，密碼一律讀環境變數不寫死；script header 附 `mongorestore` 還原說明。
  - `./backups/` 加入 `.gitignore`，不 commit 任何 dump 檔。

- **GHCR 預建映像為預設執行路徑（profile `build` 為 opt-in）**
  - `docker-compose.yml` 預設 app service 改用 `image: ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}`，`docker compose up` 直接 pull 預建映像。
  - 本機建置移入 `app-build`（profile `build`），以 YAML anchor 共用 app 設定並標記相同的 `image:` tag，使 `docker compose --profile build build` 產出的映像與 GHCR 慣例一致。
  - 新增 GitHub Actions workflow `.github/workflows/publish-image.yml`：於 version tag（`v*`）push 時（單一觸發來源，加 `concurrency` 防同 ref 並行），build + push multi-arch（`linux/amd64,linux/arm64`）映像至 `ghcr.io/fhcst/dprs`，tag 規則沿用 `scripts/docker-build.sh`。

## Capabilities

### New Capabilities

- `deployment-infrastructure`: 正式部署的基礎設施面向 —— Cloudflare Tunnel 唯一對外入口（不曝露 host 8000）、reverse-proxy 信任設定（`FORWARDED_ALLOW_IPS` 連動 Secure cookie）、MongoDB `mongodump`/`mongorestore` 備份機制。

### Modified Capabilities

- `docker-buildx`: 既有 capability 涵蓋 `scripts/docker-build.sh` 的 image-name 推導與 semver tag 展開慣例。本次新增「GitHub Actions 於 version tag 自動 publish multi-arch 映像」與「docker-compose 預設 pull GHCR 映像、本機 build 改為 opt-in profile」兩組需求，沿用同一套 image-name + tag 慣例。

## Impact

- 變更檔案：`docker-compose.yml`（cloudflared/app-build service、profiles、anchors、image 預設、密碼改走環境變數/config 檔避免進 argv、loopback port 綁定）、`.env.example`（tunnel/backup/forwarded 變數、`FASTAPI_APP_ENVIRONMENT` 預設改 prod）、`.gitignore`（`./backups/`、`docker-compose.override.yml`）。
- 新增檔案：`scripts/backup.sh`、`docker-compose.dev.yml`（本機 dev overlay，不自動合併、需顯式 `-f`）、`.github/workflows/publish-image.yml`。
- 相依工具：`docker compose`、`docker buildx`、Cloudflare Tunnel（dashboard 設定的 remotely-managed tunnel）、`mongodump`/`mongorestore`。
- 不更動 application Python 行為；不更動 cookie SameSite 與 CSRF 策略（僅在前方加入受信任 reverse proxy，與 `docs/security-notes.md` SEC-DESIGN-001 一致）。
- Bootstrapping 注意：在首個映像 publish 至 GHCR 前，`docker compose up` 無法 pull，使用者須先跑 `docker compose --profile build build`。
