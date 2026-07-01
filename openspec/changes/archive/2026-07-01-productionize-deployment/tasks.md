## 1. Cloudflare Tunnel 對外入口

- [x] 1.1 在 `docker-compose.yml` 新增 `cloudflared` service 於 `profiles: [tunnel]`（image `cloudflare/cloudflared:latest`、`command: tunnel --no-autoupdate run`、`restart: unless-stopped`、`depends_on: app`、注入 `TUNNEL_TOKEN`/`TUNNEL_TRANSPORT_PROTOCOL`），落實「Cloudflare Tunnel 作為唯一對外入口，tunnel 模式不曝露 host 8000」設計；行為：`docker compose --profile tunnel up` 會啟動 cloudflared 並經 compose network 觸達 `app:8000`，repo 內無 `config.yml`/credentials（Cloudflare Tunnel as the sole public ingress）。驗證：`docker compose --profile tunnel config -q` exit 0，並人工確認無 credentials 檔。
- [x] 1.2 從預設 `app` service 移除 `8000:8000` host publish；本機 dev 直連改由**不自動合併**的 `docker-compose.dev.yml` overlay 提供（以 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 顯式疊加，重新 publish `127.0.0.1:8000:8000`、掛載 `./src`、並覆寫 `FASTAPI_APP_ENVIRONMENT=dev`）；另在 `.gitignore` 防呆禁止提交會自動合併的 `docker-compose.override.yml`。行為：因 `docker-compose.dev.yml` 不會被自動合併，正式機 `docker compose --profile tunnel up`（毋須任何 `-f` 排除）host 即不曝露任何 app port；本機 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 則於 `127.0.0.1:8000` 可直連（Application not publicly reachable on host port 8000 in tunnel mode）。採用不自動合併的 dev overlay，是為了讓 tunnel 與 dev 兩情境可同時成立、不再互相矛盾。驗證：`docker compose --profile tunnel config` 不含 app `ports`；`docker compose -f docker-compose.yml -f docker-compose.dev.yml config` 含 `127.0.0.1:8000` 且 app `FASTAPI_APP_ENVIRONMENT=dev`。

## 2. Reverse proxy 信任與 Secure cookie

- [x] 2.1 為 app 設定 `FORWARDED_ALLOW_IPS`（文件化的 docker bridge CIDR）使其信任 cloudflared 的 `X-Forwarded-Proto: https`，落實「FORWARDED_ALLOW_IPS 信任 cloudflared，連動 Secure cookie 與 scheme 偵測」設計；行為：tunnel 後端 request scheme 判為 https、Secure cookie 端到端成立（Trusted reverse proxy forwarding for end-to-end Secure cookies）。驗證：`.env.example` 含 `FORWARDED_ALLOW_IPS` 與 guidance，compose app env 帶入該值；文件要求 tunnel/prod 須設 `FASTAPI_APP_ENVIRONMENT=prod`。
- [x] 2.2 在 design.md 與 `.env.example` 明示「SEC-DESIGN-001：CSRF / SameSite 策略不變（僅新增受信任 reverse proxy）」，落實「CSRF and SameSite strategy unchanged by tunnel introduction」需求；行為：cookie `SameSite=Lax` 與 JSON-API CSRF（CORS preflight + SameSite）不被本次變更更動。驗證：人工 review design.md 含 SEC-DESIGN-001 段落且與 `docs/security-notes.md` 一致；未變更 `src/shared/csrf.py`。

## 3. MongoDB 備份

- [x] 3.1 新增 `scripts/backup.sh`，落實「MongoDB 備份採 scripts/backup.sh + mongodump，密碼讀環境變數」設計；行為：以 `MONGO_ROOT_USERNAME`/`MONGO_ROOT_PASSWORD`/`MONGO_DB_NAME`（讀 env、不寫死）跑 `mongodump`，輸出 `./backups/` 下帶時間戳 gzip archive，idempotent，header 附 `mongorestore` 還原說明（MongoDB backup via mongodump with credentials from environment）。驗證：`bash -n scripts/backup.sh` 通過；重跑產生兩個不同時間戳檔；密碼不出現於 script 字面值。
- [x] 3.2 將 `./backups/` 加入 `.gitignore`；行為：dump 檔不被 git 追蹤。驗證：`git check-ignore backups/x.gz` 命中；`git status` 不顯示 dump 檔。

## 4. GHCR 預建映像為預設執行路徑

- [x] 4.1 將預設 `app` service 改為 `image: ghcr.io/fhcst/dprs:${APP_IMAGE_TAG:-latest}`，並以 YAML anchor 抽出共用設定新增 `app-build`（`profiles: [build]`、`build: .`、相同 `image:` tag），落實「GHCR 預建映像為預設，本機 build 改為 opt-in profile」設計；行為：`docker compose up` 直接 pull 預建映像、`docker compose --profile build build` 產出同名同 tag 本機映像（GHCR image as the default compose run path）。驗證：`docker compose config -q` 與 `docker compose --profile build config -q` exit 0；config 輸出顯示 app 用 GHCR image、app-build 帶 build context 與相同 tag。
- [x] 4.2 於 design.md、`.env.example` 與 README 短註記錄 bootstrapping caveat：首個映像 publish 前須先 `docker compose --profile build build`，並新增 `APP_IMAGE_TAG`〔選填，預設 latest〕至 `.env.example`；行為：首次使用者照文件可成功啟動。驗證：人工 review 三處文件均含 caveat 與 `APP_IMAGE_TAG`。

## 5. CI 自動 publish 映像

- [x] 5.1 新增 `.github/workflows/publish-image.yml`，落實「GitHub Actions 於 version tag 自動 publish multi-arch 映像」設計；行為：僅於 push tag `v*` 觸發（單一觸發來源 + `concurrency` 防同 ref 並行，不掛 `release: published` 以免同版本 build/push 兩次），使用 setup-qemu / setup-buildx / login（ghcr.io、`${{ github.actor }}`、`${{ secrets.GITHUB_TOKEN }}`）/ build-push（`platforms: linux/amd64,linux/arm64`），tag 由 metadata-action 依 semver 展開、比照 `scripts/docker-build.sh`（`v1.2.3` → `:1 :1.2 :1.2.3 :latest`；pre-release 不展開、不更新 latest），`permissions: contents: read, packages: write`，無寫死 secret（GitHub Actions publishes the multi-arch image on version tags）。驗證：workflow YAML 可被 `yaml.safe_load` 解析；人工 review tag 規則與 `dsl-engine.yml` house style 對齊。

## 6. 驗證

- [x] 6.1 驗證 compose 在所有 profile 組合下解析正確；行為：`docker compose config -q`（預設）與 `docker compose --profile tunnel --profile build --profile backup config -q` 均 exit 0（docker 不可用時改做 YAML 結構驗證並於回報說明）。驗證：上述指令 exit 0。
- [x] 6.2 執行 `spectra validate productionize-deployment` 並修正至通過；行為：change artifacts 結構與 cross-reference 一致。驗證：validate 回報 pass。
