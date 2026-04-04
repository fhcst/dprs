## Context

本專案（DPRS）的 Dockerfile 採雙階段建置：Stage 1 用 Rust + PyO3/maturin 編譯 DSL engine wheel，Stage 2 為 Python runtime。原本沒有跨平台建置流程，維護者需要手動輸入 docker 指令，且無版本化規則。

本設計在此背景下引入 `scripts/docker-build.sh`，讓維護者能以單一指令完成跨平台建置與推送，並以 git tag 作為版本來源，無需維護額外的版本設定檔。

**現有 Dockerfile 特性（會影響設計）：**
- Stage 1 含 Rust 編譯（maturin）：跨平台時 QEMU 模擬速度慢，但行為正確，不需要額外的 cross-compilation toolchain
- 不涉及 Docker secrets 或 build-time sensitive data

---

## Goals / Non-Goals

**Goals:**

- 以 git remote origin URL 自動推導 image name，與 GitHub 官方 CI 慣例一致（`ghcr.io/<owner>/<repo>`）
- 以 git tag 驅動版本，semver tag 自動展開為 shorthand tags + `latest`
- 一步完成 multi-platform build + push（`linux/amd64` + `linux/arm64`）
- 支援 `--dry-run` 以便在不實際推送的情況下驗證輸出
- 腳本本身包含 self-test（`--test`），驗證純邏輯（URL 解析、tag 展開）

**Non-Goals:**

- 不整合 GitHub Actions CI（本 script 供手動執行）
- 不處理 GHCR 登入（前置條件：使用者自行 `docker login ghcr.io`）
- 不修改 Dockerfile
- 不支援 Windows（sh/bash 腳本）

---

## Decisions

### Image name 從 git remote 動態推導，而非寫死在設定檔

OSS 慣例（GitHub 官方文件、containerd/nerdctl、docker/buildx 等）一律從 `github.repository`（即 `<owner>/<repo>`）動態推導 image name，而非寫死在 `pyproject.toml` 或其他設定檔。

**採用：** `git remote get-url origin` → 解析 HTTPS/SSH URL → 組成 `ghcr.io/<owner>/<repo>`

**捨棄：** 在 `pyproject.toml` 加 `[tool.docker] image = "..."` — 語言套件的 metadata 不應混入 deployment infrastructure 設定；也不符合任何既有慣例，會讓其他貢獻者困惑。

**優點：** fork / 換 org 後只需更新 git remote，腳本自動正確；無需同步維護兩個地方。

---

### 版本來源：git tag（exact match），fallback 到 commit hash

版本唯一來源是 git tag（`git describe --tags --exact-match HEAD`）。

**採用：** exact match only — 只有打了 tag 的 commit 才算正式版本。

**捨棄：** `git describe`（帶 commit offset，如 `v1.2.3-5-gabcdef`）— 這種格式不是合法的 Docker tag 格式（含 `+` 或特殊字元），且語義不清楚，不應自動推送到 registry。

**Fallback：** 無 tag 時輸出 `:sha-<7-char-hash>`，不更新 `:latest`。這讓維護者可以推送開發快照而不污染正式版本通道。

---

### Semver tag 展開策略：major=0 略過 `:major`

語意版本慣例（SemVer 2.0）中 major=0 代表 API 不穩定，因此 `:0` tag 沒有實際意義（下一個版本可能是 `:0` 指向完全不同的東西）。

**採用：**
- major ≥ 1：展開 `:M`, `:M.N`, `:M.N.P`, `:latest`
- major = 0：展開 `:M.N`, `:M.N.P`, `:latest`（略過 `:M`）

**Pre-release：** 只輸出完整版本 tag（如 `:1.0.0-rc1`），不展開、不更新 `:latest`。Pre-release 不應透過 `:latest` 意外被一般使用者拉到。

---

### 使用 docker-container driver 的 buildx builder 管理

Multi-platform build 需要 `docker-container` driver（預設的 `docker` driver 只支援本機架構）。

**採用：** 腳本以固定名稱 `dprs-multiplatform` 管理 builder instance，idempotent（`docker buildx inspect` 先檢查是否存在，不存在才建立）。

**捨棄：** 使用臨時 builder（不命名）— 每次執行都建立新 builder，佔用資源且速度慢（需重新 bootstrap）。

---

### 不使用 `eval`，以 bash array 組合 docker 指令

Security 原則：絕不將使用者輸入 interpolate 進字串再 eval。`--tag` 參數以 array `tag_args+=(--tag "$t")` 累積，最終以 `"${tag_args[@]}"` 展開。

---

### 跨平台建置採 QEMU emulation，不額外設定 cross-compilation

Dockerfile Stage 1 含 Rust/maturin 編譯，為非本機架構時會透過 QEMU 模擬執行。雖然速度較慢（非本機架構約慢 5-10 倍），但行為與本機建置完全一致，不需要修改 Dockerfile 或引入 cross-compilation toolchain（後者複雜度高，且 maturin 的 cross-compilation 設定需要額外的 linker 設定）。

---

## Risks / Trade-offs

**[風險] QEMU 模擬下 Rust 編譯極慢** → 接受此 trade-off；手動觸發建置，不在 hot path 上。若未來 CI 化，可考慮 `--cache-from` 加速或使用 native runners。

**[風險] builder `dprs-multiplatform` 在部分 CI 環境不存在** → 本 script 設計為本地手動執行，不涉及 CI；CI 場景應改用 `docker/setup-buildx-action`。

**[風險] git remote URL 格式多樣性** → 目前只處理 HTTPS 和 SSH 兩種主流格式，其他（如 `ssh://git@...`、GitLab、Bitbucket）可能解析失敗。失敗時報錯提示使用者改用 `--image` 參數手動指定。

**[風險] bash 版本相容性** → `${var,,}` 語法（小寫轉換）需要 bash 4+，macOS 內建 bash 3.2 不支援。已改用 `tr '[:upper:]' '[:lower:]'`，相容 bash 3.2+。

---

## Migration Plan

1. 確認 Docker Desktop 或 Docker Engine 已安裝且 buildx 可用（`docker buildx version`）
2. 登入 GHCR：`docker login ghcr.io`
3. 建立 git tag（如 `git tag v0.5.0`）
4. 執行 `scripts/docker-build.sh --dry-run` 確認輸出符合預期
5. 執行 `scripts/docker-build.sh` 正式推送

Rollback：docker image tag 一旦推送即存在 registry，無法刪除版本歷史中的 `:latest`（只能覆蓋）。若推錯版本，應盡快以正確版本重新推送覆蓋 `:latest`。
