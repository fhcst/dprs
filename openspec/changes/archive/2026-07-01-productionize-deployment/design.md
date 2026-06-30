## Context

DPRS（daily-training-submit-system）目前的部署素材：

- `Dockerfile`：三階段 multi-arch 建置（`TARGETARCH`-aware：dsl-builder 編 Rust+WASM、tailwind downloader、slim runtime）。runtime 已有 `ENV FORWARDED_ALLOW_IPS=""`，連動 uvicorn `--forwarded-allow-ips`。
- `scripts/docker-entrypoint.sh`：先跑 migration，再依 `FASTAPI_APP_ENVIRONMENT`（`prod`/`production` 為 production 模式，其餘為 dev）啟動 fastapi。
- `scripts/docker-build.sh`：已能由 git remote 推導 `ghcr.io/<owner>/<repo>`，由 git tag 展開 `:1 :1.2 :1.2.3 :latest`（無 tag → `:sha-<hash>`），multi-arch build + push。本次所有 image-name/tag 慣例一律沿用，不另立新規。
- `docker-compose.yml`：`app`（`build: .`、publish `8000:8000`、mount `./src`）、`mongo`（`mongo:7.0`、綁 `127.0.0.1:27017`、volume `mongo_data`、healthcheck）、`redis`（綁 `127.0.0.1:6379`、healthcheck）、`mongo-express`（profile `debug`）。
- `.env.example`：已記錄 `FASTAPI_APP_ENVIRONMENT`、`SESSION_SECRET`、`MONGO_*`、`REDIS_PASSWORD`、`ME_*`。`.env` 已 gitignore。
- 既有唯一 workflow：`.github/workflows/dsl-engine.yml`，新 workflow 沿用其風格。

本次為純 infra / docker-compose / CI 變更，**不改動 application Python 行為**。約束：不得執行 git commit/push，不得 docker login 或實際 push 映像，不得放入任何真實 secret/token（僅 placeholder）。

## Goals / Non-Goals

**Goals:**

- 以 Cloudflare Tunnel 作為正式部署的**唯一**對外入口，host 不曝露 8000。
- 讓 app 在 tunnel 後端正確判定 HTTPS scheme，使 Secure cookie 端到端成立。
- 提供簡單、可重複執行、密碼不寫死的 MongoDB 備份（含還原說明）。
- 把 GHCR 預建映像設為 `docker compose up` 的預設路徑，本機 build 改為 opt-in profile。
- 以 GitHub Actions 在 version tag（`v*`）push 時自動 publish multi-arch 映像，tag 規則與 `scripts/docker-build.sh` 一致。

**Non-Goals:**

- 不改動 application Python 行為、不改動 cookie SameSite 或 CSRF 策略。
- 不在本次實際 build/push 任何映像（CI 僅在跑 tag 時才真正 publish）。
- 不在 repo 內放置 Cloudflare Tunnel 的 `config.yml`/credentials（採 dashboard 管理的 remotely-managed tunnel）。
- 不引入 secrets manager、不改 Dockerfile 既有階段邏輯。
- 不處理 mongo 以外的服務備份（redis 為 cache，可重建）。

## Decisions

### Cloudflare Tunnel 作為唯一對外入口，tunnel 模式不曝露 host 8000

新增 `cloudflared` service 於 `profiles: [tunnel]`，採 `cloudflare/cloudflared:latest` 搭配 `command: tunnel --no-autoupdate run`，token-based remotely-managed tunnel —— ingress route（指向 `http://app:8000`）於 Cloudflare dashboard 設定，repo 內**不需** `config.yml` 或 credentials 檔。`restart: unless-stopped`、`depends_on: app`。token 與 protocol 由 `.env` 注入（`TUNNEL_TOKEN`、`TUNNEL_TRANSPORT_PROTOCOL`，後者值域 `auto|http2|quic`）。

關鍵安全決策：tunnel 模式下，對外**只**能有 tunnel 一條路徑。因此把 app 的 `8000:8000` host publish 從預設 service 移除 —— cloudflared 透過 compose network 以 service name `app:8000` 觸達 app，毋須 host port。淨效果：`docker compose --profile tunnel up` 在 host 上不曝露任何 port，只經 Cloudflare edge 對外。

**採用：** 預設 `app` service 不含 `ports:`；本機 dev 需要直連時，以顯式 `-f` 疊加 `docker-compose.dev.yml`（`docker compose -f docker-compose.yml -f docker-compose.dev.yml up`），重新 publish `127.0.0.1:8000:8000` 並覆寫 `FASTAPI_APP_ENVIRONMENT=dev`。關鍵：`docker-compose.dev.yml`**不會被自動合併**（只有同名的 `docker-compose.override.yml` 才會被 compose 在每個無 `-f` 的 `up` 自動合併，且與 profile 無關）。因此「正式 tunnel 部署」用 `docker compose --profile tunnel up` 結構上即保證 portless、完全不受 dev overlay 影響；「本機 dev 直連」則以顯式 `-f` 啟用，兩者各自明確且可同時成立（不再像自動合併的 override 那樣兩個情境互相矛盾）。

**捨棄：** 在 cloudflared service 寫死 `config.yml` + credentials 檔 —— 會把 tunnel 機密帶進 repo、且 route 變更需改檔重建；remotely-managed（dashboard + token）更符合最小機密原則。

**捨棄：** 維持 app 預設 publish 8000、僅靠防火牆擋 —— 與「唯一入口」目標相違，且容易因環境差異漏擋。

### FORWARDED_ALLOW_IPS 信任 cloudflared，連動 Secure cookie 與 scheme 偵測

Cloudflare Tunnel 在 edge 終結 TLS，browser↔edge 為 HTTPS，但 cloudflared↔app 在 compose network 內是 plain HTTP。app 需信任 cloudflared 送來的 `X-Forwarded-Proto: https`，uvicorn 才會把 request scheme 判為 https，Secure cookie 與任何 scheme 相關邏輯才能端到端正確。

uvicorn 的 `--forwarded-allow-ips` 已由 Dockerfile `ENV FORWARDED_ALLOW_IPS=""` 連動。本次在 tunnel 部署為 app 設定 `FORWARDED_ALLOW_IPS` 為受信任值 —— 由於 cloudflared 與 app 同在 docker bridge network，來源 IP 為該 network 的 container IP，採文件化的 docker bridge CIDR（例如 `172.16.0.0/12`，預設 docker bridge 範圍）作為信任來源；`.env.example` 會附說明與保守替代值。此設定為 tunnel 後端 Secure cookie 正確運作的**必要條件**。

**採用：** `.env` 注入 `FORWARDED_ALLOW_IPS`（tunnel 部署填 docker bridge CIDR），預設 dev 留空（不信任任何 proxy）。

**捨棄：** `FORWARDED_ALLOW_IPS=*`（信任所有來源）—— 在 host 不曝露 8000 的前提下風險已低，但保留明確 CIDR 仍是較佳實踐，避免日後有人加 publish 時意外讓任意來源偽造 `X-Forwarded-*`。

並於文件明示：tunnel/prod 部署時操作者**必須**設定 `FASTAPI_APP_ENVIRONMENT=prod`，Secure cookie 與 SESSION_SECRET guard 才會啟用（tunnel 在 Cloudflare edge 終結 TLS，browser↔edge 為 HTTPS）。

### GHCR 預建映像為預設，本機 build 改為 opt-in profile

預設 `app` service 改用 `image: ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}`，`docker compose up` 直接 pull 預建映像，換機部署免在每台機器重編 Rust/WASM。本機建置移入第二個 service `app-build`（`profiles: [build]`），其 `build: .` 並標記**相同**的 `image:` tag，使 `docker compose --profile build build` 產出的本機映像與 GHCR 慣例同名同 tag。

為避免重複 app 設定（env、depends_on 等），以 YAML anchor 抽出共用片段（`x-app-base: &app-base`），`app` 與 `app-build` 各自 `<<: *app-base` 後再加差異（`app` 無 `build`，`app-build` 加 `build: .` 與 `profiles: [build]`）。

**採用：** anchor 共用 + 兩個 service。`APP_IMAGE_TAG` 由 env 控制（預設 `latest`）。

**捨棄：** 同一 service 同時寫 `build:` 與 `image:`（compose 會在 build profile 下 build、否則 pull，但語義模糊且無法乾淨地以 profile 切換「只 pull / 只 build」）—— 拆成兩個 service 並以 profile 區隔，意圖最清楚。

**Bootstrapping caveat（必記文件）：** 在首個映像 publish 至 GHCR 之前，`docker compose up` 無法 pull `ghcr.io/fhcst/dprs:latest`。首次使用者**必須**先 `docker compose --profile build build` 產生本機映像（同 tag），之後 `docker compose up` 才能直接起。此點寫入 design.md、`.env.example` 與 README 短註。

### GitHub Actions 於 version tag 自動 publish multi-arch 映像

新增 `.github/workflows/publish-image.yml`，僅於 push version tag（`v*`）時觸發（單一觸發來源，避免與 `release: published` 重複 build/push；另加 `concurrency` group 防同 ref 並行）。沿用 `dsl-engine.yml` 風格，使用 `docker/setup-qemu-action` + `docker/setup-buildx-action` + `docker/login-action`（registry `ghcr.io`、username `${{ github.actor }}`、password `${{ secrets.GITHUB_TOKEN }}`）+ `docker/build-push-action`（`platforms: linux/amd64,linux/arm64`）。tag 由 git tag 推導，比照 `scripts/docker-build.sh` 規則（`v1.2.3` → `:1 :1.2 :1.2.3 :latest`；pre-release 不展開、不更新 latest），以 `docker/metadata-action` 產生。`permissions: contents: read, packages: write`。不寫死任何 secret。實際 publish **僅**在 CI 跑於 tag 時發生；本變更只建置自動化，不在此處 build/push。

**採用：** `docker/metadata-action` 的 `type=semver` patterns（`{{major}}`、`{{major}}.{{minor}}`、`{{version}}`）對應 `scripts/docker-build.sh` 的展開，並以 `flavor: latest=auto` 對齊 pre-release 不更新 latest 的行為。

**捨棄：** 在 CI 直接呼叫 `scripts/docker-build.sh` —— 該腳本依賴本機 git tag 與互動式 builder 管理，CI 場景用官方 actions 更標準、cache 更友善（與 `dsl-engine.yml` 既有 actions 生態一致）。

### MongoDB 備份採 scripts/backup.sh + mongodump，密碼讀環境變數

新增 `scripts/backup.sh`：讀取與 compose 相同的 env 變數（`MONGO_ROOT_USERNAME`、`MONGO_ROOT_PASSWORD`、`MONGO_DB_NAME`），對執行中的 mongo container 跑 `mongodump`（archive + gzip），輸出 `./backups/dprs-<dbname>-YYYYmmdd-HHMMSS.archive.gz`。idempotent（重跑只是多一個帶新時間戳的檔，不覆蓋、不互相干擾），`mkdir -p ./backups` 確保目錄存在。密碼**一律**讀 env，不寫死、不出現在 process 列表外洩（透過 container 內執行或 `--quiet`）。script header 附 `mongorestore --gzip --archive=<file>` 還原說明。`./backups/` 加入 `.gitignore`，絕不 commit dump。

**採用：** 透過 `docker compose exec -T mongo mongodump ... --archive --gzip` 在 mongo container 內執行，stdout 導向 host 的 `./backups/` 檔；如此不需 host 安裝 mongo tools。

**捨棄（保留為選配）：** 常駐的 `mongo-backup` service（`profiles: [backup]`）做排程 dump —— 列為 optional，本次以 `scripts/backup.sh` 為主，文件說明可後續加排程。

### SEC-DESIGN-001：CSRF / SameSite 策略不變（僅新增受信任 reverse proxy）

本變更**不**更動 `src/shared/csrf.py` 的 CSRF 行為，也**不**更動 cookie 的 `SameSite=Lax` 設定。依 `docs/security-notes.md` SEC-DESIGN-001，JSON API 的 CSRF 防護依賴 CORS preflight（`application/json` 為 non-simple content type）+ `SameSite=Lax` cookie 雙層防護。Cloudflare Tunnel 只是把 app 放到一個**受信任的 reverse proxy** 後面（edge 終結 TLS、轉發 `X-Forwarded-*`），瀏覽器看到的 origin / cookie 行為不變，因此與 SEC-DESIGN-001 完全一致、不需重新評估 CSRF 策略。`FORWARDED_ALLOW_IPS` 僅影響 scheme 偵測（讓 Secure cookie 正確），不改變 SameSite 或 CORS 政策。此點在文件明確標註，避免日後誤以為「加了 proxy 要改 cookie 設定」。

## Implementation Contract

本變更為 infra/CI artifact 變更，apply 階段需交付下列可觀察行為：

**docker-compose.yml**

- 預設（無 profile）`docker compose config` 解析成功，且 `app` service 使用 `image: ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}`、**不含** host `ports` publish 8000、保留既有 env（`FASTAPI_APP_ENVIRONMENT`、`SESSION_SECRET`、`MONGO_URL`、`REDIS_URL`）與 `depends_on`（mongo/redis healthy）。
- 存在 `app-build` service（`profiles: [build]`），含 `build: .` 且 `image:` 與 `app` 相同；以 YAML anchor 共用設定，避免重複。
- 存在 `cloudflared` service（`profiles: [tunnel]`），`image: cloudflare/cloudflared:latest`、`command: tunnel --no-autoupdate run`、`restart: unless-stopped`、`depends_on: app`，注入 `TUNNEL_TOKEN`、`TUNNEL_TRANSPORT_PROTOCOL`。
- 保留 `mongo`、`redis`、`mongo-express`（profile `debug`）與 top-level `volumes: mongo_data` 不破壞。
- 可選 `mongo-backup` service 若加入，須在 `profiles: [backup]`。
- 驗收：`docker compose config -q`（預設）與 `docker compose --profile tunnel --profile build --profile backup config -q` 均 exit 0；若無 docker，則 YAML 結構驗證通過並於回報說明。

**docker-compose.dev.yml（本機 dev overlay；已進 repo，不自動合併）**

- 提供本機 dev 直連 overlay：以 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 顯式疊加，重新 publish `127.0.0.1:8000:8000` 至 app、掛載 `./src`、覆寫 `FASTAPI_APP_ENVIRONMENT=dev`。因檔名非 `docker-compose.override.yml`，compose **不會**自動合併它，故正式機 `docker compose --profile tunnel up` 不受影響、不曝露 host port。另在 `.gitignore` 防呆禁止提交會自動合併的 `docker-compose.override.yml`。文件說明此檔用途。

**.env.example**

- 新增 `TUNNEL_TOKEN`〔必填，tunnel profile，placeholder only〕、`TUNNEL_TRANSPORT_PROTOCOL`〔選填，預設 auto〕、`FORWARDED_ALLOW_IPS`（含 tunnel 部署填 docker bridge CIDR 的 guidance）、`APP_IMAGE_TAG`〔選填，預設 latest〕，以及 tunnel/prod 須設 `FASTAPI_APP_ENVIRONMENT=prod` 的說明。全部 Taiwan-Traditional-Chinese 註解，無真實 token。

**scripts/backup.sh**

- 可執行（shebang + `set -euo pipefail`），讀 `MONGO_ROOT_USERNAME`/`MONGO_ROOT_PASSWORD`/`MONGO_DB_NAME`，產出 `./backups/` 下帶時間戳的 gzip archive；密碼不寫死、不硬編。header 含 `mongorestore` 還原說明。重跑 idempotent。
- 驗收：`bash -n scripts/backup.sh` 語法通過；header 說明可人工 review；`./backups/` 已在 `.gitignore`。

**.github/workflows/publish-image.yml**

- 僅於 `push` tag `v*` 觸發（單一觸發來源，避免與 `release: published` 重複 build/push），並加 `concurrency` group 確保同 ref 不並行；jobs 使用 setup-qemu / setup-buildx / login（ghcr.io、github.actor、`GITHUB_TOKEN`）/ build-push（`platforms: linux/amd64,linux/arm64`），tags 由 metadata-action 依 semver 展開，對齊 `scripts/docker-build.sh`。`permissions: contents: read, packages: write`。無寫死 secret。
- 驗收：workflow YAML 能被解析（`python -c yaml.safe_load` 或等價）；內容人工 review 對齊 tag 規則。

**.gitignore**

- 含 `./backups/`（或 `backups/`），不 commit 任何 dump。

**範圍邊界（明確不做）：** 不改 application Python；不改 cookie SameSite / CSRF；不改 Dockerfile 既有階段；不實際 build/push 映像；不放真實 token；不執行 git commit/push（留檔給 main session）。

## Risks / Trade-offs

- [風險] 首個映像未 publish 前 `docker compose up` 無法 pull → 文件（design.md / `.env.example` / README）明示首次須先 `docker compose --profile build build`。
- [風險] `FORWARDED_ALLOW_IPS` 設太寬（如 `*`）可能讓偽造 `X-Forwarded-*` → 採文件化 docker bridge CIDR 而非 `*`，且 tunnel 模式 host 不曝露 8000，攻擊面已小。
- [風險] tunnel 模式忘了設 `FASTAPI_APP_ENVIRONMENT=prod`，Secure cookie 不啟用 → 文件明確要求；prod guard 亦會擋預設 SESSION_SECRET。
- [風險] 自動合併的 `docker-compose.override.yml` 在正式機被誤套用而重新曝露 8000 → 本機 dev overlay 改用**不自動合併**的 `docker-compose.dev.yml`（需顯式 `-f`），正式機 `docker compose --profile tunnel up` 結構上即保證 portless（不依賴操作者記得帶或排除任何 `-f`）；並在 `.gitignore` 防呆禁止提交 `docker-compose.override.yml`，杜絕該 foot-gun 進入 repo。
- [風險] cloudflared token 外洩 → token 只存在 `.env`（gitignore），repo 內僅 placeholder；remotely-managed tunnel 可於 dashboard 即時撤銷。
- [風險] backup 期間 mongo 寫入造成快照不一致 → `mongodump` 對單機 replica/standalone 提供 point-in-time 近似；如需嚴格一致性，文件可建議停機或 fsyncLock（列為後續）。
- [Trade-off] CI 用官方 actions 而非 `scripts/docker-build.sh`：兩處 tag 邏輯需保持同步 → design 明列「比照 docker-build.sh 規則」，spec 以 scenario 釘住對應關係。

## Migration Plan

1. 把 `.env.example` 新增變數複製到 `.env` 並填值（tunnel 部署填 `TUNNEL_TOKEN`、`FORWARDED_ALLOW_IPS`、設 `FASTAPI_APP_ENVIRONMENT=prod`）。
2. 首次部署：`docker compose --profile build build` 產生本機映像（在 GHCR 尚無映像時），或等 CI 在 `v*` tag publish 後直接 `docker compose pull`。
3. 於 Cloudflare dashboard 建立 remotely-managed tunnel、取得 token、設定 ingress 指向 `http://app:8000`。
4. 正式啟動：`docker compose --profile tunnel up -d`（host 不曝露 8000，僅經 Cloudflare）。
   > 因本機 dev overlay 改用不自動合併的 `docker-compose.dev.yml`，正式機 `docker compose --profile tunnel up` 結構上即不曝露 host port、毋須帶 `-f` 排除任何檔；只有本機 dev 才需顯式 `-f docker-compose.yml -f docker-compose.dev.yml`。
5. 定期備份：`scripts/backup.sh`（可掛 cron）。還原：`mongorestore --gzip --archive=./backups/<file>`。
6. Rollback：tunnel 可於 dashboard 停用；compose 可 `docker compose --profile tunnel down`；映像可用舊 `APP_IMAGE_TAG` 重新 `docker compose up`。

## Open Questions

- 是否要正式納入常駐 `mongo-backup`（profile `backup`）排程 service，或維持 `scripts/backup.sh` + 外部 cron？本次以 script 為主，service 列為選配。
- `FORWARDED_ALLOW_IPS` 是否改用更精確的單一 cloudflared container IP（需 static IP 指派）而非 bridge CIDR？目前採 CIDR 以求簡單，可後續收斂。
