## 1. 版本號與 Config 更新

- [x] [P] 1.1 [Package version numbers are consistent at 1.0.0] 更新 `pyproject.toml`：將 `version` 從 `"0.5.0"` 改為 `"1.0.0"`
- [x] [P] 1.2 [Package version numbers are consistent at 1.0.0] 更新 `crates/dsl-engine/Cargo.toml`：將 `version` 從 `"0.1.0"` 改為 `"1.0.0"`
- [x] [P] 1.3 [Package version numbers are consistent at 1.0.0] 更新 `crates/dsl-engine/pyproject.toml`：將 `version` 從 `"0.1.0"` 改為 `"1.0.0"`
- [x] [P] 1.4 更新 `openspec/config.yaml`：在 `context` 欄位填入專案技術堆疊說明（FastAPI、Beanie、MongoDB、Redis、Rust DSL Engine、WASM、PyO3、繁體中文 locale）

## 2. README 改版

- [x] [P] 2.1 [README follows OSS project conventions] 在 `README.md` 最頂部插入 `banner.png` 圖片（`![DPRS Banner](banner.png)`）
- [x] [P] 2.2 [README follows OSS project conventions] 在 banner 下方加入 badge strip：CI 狀態（GitHub Actions）、授權（ECL-2.0）、版本（1.0.0）
- [x] 2.3 [README follows OSS project conventions] 將現有功能特色段落重構為精簡的 feature overview（保留重點，移除過度詳細的 sub-bullet）
- [x] 2.4 [README follows OSS project conventions] 重寫 Quick Start 章節：僅保留 Docker Compose 最短路徑（三個步驟內可啟動服務），移除本機開發步驟（改連結 docs/getting-started.md）
- [x] 2.5 [README follows OSS project conventions] 移除 `README.md` 中的環境變數明細表格，替換為指向 `docs/configuration.md` 的連結
- [x] 2.6 [README follows OSS project conventions] 確認文件索引表完整且所有連結有效

## 3. CHANGELOG v1.0.0 條目

- [x] 3.1 在 `CHANGELOG.md` 頂部新增 `## [1.0.0] - 2026-04-04` 條目，涵蓋：DSL Engine、徽章管理 v2（Detail/Revoke）、邀請碼審核、安全強化（IDOR/timing/CSRF/rate-limit/JWT 啟動檢查）、Docker Buildx 腳本、環境變數修復

## 4. 教師操作文件更新

- [x] 4.1 [Teacher workflow documentation is UI-centric and current] 移除 `docs/user-guide/teacher-workflow.md` 所有章節末尾的「對應 API」code block 與 API Reference 速查表
- [x] 4.2 [Teacher workflow documentation is UI-centric and current] 更新第 9.2 節「徽章」：描述徽章 Detail Modal 操作（點擊徽章卡片開啟 Modal，查看已/未獲得學生清單）與 Soft Delete Revoke 步驟
- [x] 4.3 [Teacher workflow documentation is UI-centric and current] 新增「DSL 觸發規則管理」章節（第 9.x 節）：說明進入觸發規則管理頁、在 CodeMirror 編輯器撰寫 DSL 表達式、使用 autocomplete 與 hover hint、執行 dry-run 測試、儲存規則

## 5. 架構文件更新

- [x] 5.1 [Architecture document reflects v1.0.0 and DSL Engine] 將 `docs/architecture.md` 標頭版本從 `v0.3.0` 改為 `v1.0.0`
- [x] 5.2 [Architecture document reflects v1.0.0 and DSL Engine] 在架構圖的 Services/Providers 層加入 DSL Engine 模組（Rust/WASM/PyO3）說明框
- [x] 5.3 [Architecture document reflects v1.0.0 and DSL Engine] 在模組清單中加入 `src/gamification/triggers/`，說明其職責為評估 DSL 觸發規則並自動頒發徽章

## 6. 學生操作文件更新

- [x] 6.1 [Student workflow documents dedicated badges page] 更新 `docs/user-guide/student-workflow.md` 第 8 節：說明可直接前往 `/pages/students/me/badges` 查看完整徽章清單，而不只是 Dashboard badge strip

## 7. 快速入門文件更新

- [x] 7.1 [Getting-started documents Docker Buildx multi-arch build] 在 `docs/getting-started.md` 加入「多架構 Docker 映像建置」章節：說明 `scripts/docker-build.sh` 的前置需求（Docker Buildx）、指令範例，以及 `linux/amd64` / `linux/arm64` 雙架構支援
