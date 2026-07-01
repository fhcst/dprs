## 1. 建立腳本基礎結構

- [x] 1.1 建立 `scripts/docker-build.sh` 並設定 shebang、`set -euo pipefail`、usage 說明；不使用 `eval`，以 bash array 組合 docker 指令（安全考量）
- [x] 1.2 實作 `--image` 參數解析，允許覆蓋自動推導的 image name

## 2. Image Name 推導

- [x] 2.1 實作 image name 從 git remote 動態推導，而非寫死在設定檔：從 git remote origin URL 擷取 `<owner>/<repo>`，支援 HTTPS 與 SSH 格式，strip `.git` 後綴，組成 `ghcr.io/<owner>/<repo>`（image name derivation from git remote）

## 3. 版本偵測與 Tag 展開

- [x] 3.1 實作 版本來源：git tag（exact match），fallback 到 commit hash：用 `git describe --tags --exact-match HEAD` 取得 tag，strip `v` prefix；無 tag 時 fallback 到 `sha-<short-hash>`（version detection from git tags / commit hash fallback tag）
- [x] 3.2 實作 semver tag 展開策略：major=0 略過 `:major`；major ≥ 1 展開為 `:major`, `:major.minor`, `:major.minor.patch`, `:latest`（semver tag expansion for stable releases）
- [x] 3.3 實作 pre-release tag handling：偵測 hyphen 後的 pre-release 標記，僅產生完整版本 tag，不展開、不更新 latest

## 4. Builder 管理與建置

- [x] 4.1 實作 使用 docker-container driver 的 buildx builder 管理：以固定名稱 `dprs-multiplatform` idempotent 管理 builder instance（builder instance management）
- [x] 4.2 實作 跨平台建置採 QEMU emulation，不額外設定 cross-compilation：`docker buildx build --platform linux/amd64,linux/arm64 --push`，tag 參數以 array 展開（cross-platform build and push）

## 5. 測試驗證

- [x] [P] 5.1 手動測試：在有 semver tag 的 commit 上執行腳本，驗證 tag 展開正確
- [x] [P] 5.2 手動測試：在無 tag 的 commit 上執行腳本，驗證 fallback 到 commit hash
- [x] [P] 5.3 手動測試：使用 `--image` 參數覆蓋，驗證 override 生效
