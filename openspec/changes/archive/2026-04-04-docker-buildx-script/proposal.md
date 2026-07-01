## Why

專案目前有 Dockerfile 但缺乏跨平台建置與版本化的流程。需要一個 shell script 讓維護者能用 `docker buildx` 建立 `linux/amd64` + `linux/arm64` 的 image，並依 git tag 自動產生符合 semver 慣例的 image tag，一步完成 build + push 到 GHCR。

## What Changes

- 新增 `scripts/docker-build.sh`：跨平台 Docker image 建置腳本
  - 從 git remote origin 自動推導 image name（`ghcr.io/<owner>/<repo>`）
  - 從 git tag 讀取 semver 版本，產生展開的 tag 組合
  - 支援 `--image` 參數覆蓋自動推導的 image name
  - 使用 `docker buildx build --push` 一步完成 build + push

- Tag 策略：
  - 正式版 `v1.2.3`（major ≥ 1）→ `:1`, `:1.2`, `:1.2.3`, `:latest`
  - 正式版 `v0.3.1`（major = 0）→ `:0.3`, `:0.3.1`, `:latest`（略過 major-only tag）
  - Pre-release `v1.0.0-rc1` → `:1.0.0-rc1`（不展開、不更新 latest）
  - 無 tag → `:sha-<short-hash>`（不更新 latest）

## Non-Goals

- 不修改現有 Dockerfile
- 不建立 CI/CD pipeline（GitHub Actions）— 本 script 供手動執行
- 不處理 GHCR 登入（使用者需自行 `docker login ghcr.io`）

## Capabilities

### New Capabilities

- `docker-buildx`: 跨平台 Docker image 建置腳本，支援 semver tag 展開與 GHCR push

### Modified Capabilities

（無）

## Impact

- 新增檔案：`scripts/docker-build.sh`
- 相依工具：`docker buildx`、`git`
- 現有 `Dockerfile`、`docker-compose.yml` 不受影響
