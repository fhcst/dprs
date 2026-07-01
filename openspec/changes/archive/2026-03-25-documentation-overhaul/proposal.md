## Why

專案從 0.1.0 發展至今，功能日趨完善，但說明文件仍停留在早期狀態：`README.md` 資訊過時、`Usage.md` 未涵蓋新功能、`CONTRIBUTE.md` 已刪除未補。系統管理者、教師、學生、開發者四種角色各自需要的操作指引散落或缺失。此次一併補齊所有文件，並以 OSS 標準規格撰寫，讓任何人都能快速上手部署、使用與貢獻。

## What Changes

- 改寫 `README.md`：更新功能清單、技術堆疊、快速開始、環境變數表、文件索引，版本升至 0.5.0
- 新建 `CONTRIBUTING.md`：開發環境設定、專案結構、測試方式、Spectra 工作流程、Commit 規範
- 新建 `SECURITY.md`：安全政策、漏洞通報流程、已實施的安全措施
- 新建 `CHANGELOG.md`：回溯 0.1.0–0.3.0，加上 0.5.0 紀錄
- 新建 `docs/getting-started.md`：Docker Compose 部署 + 本機開發環境設定
- 新建 `docs/configuration.md`：所有環境變數完整說明、Docker 服務設定、生產環境注意事項
- 新建 `docs/user-guide/admin-setup.md`：系統初始設定精靈操作說明
- 新建 `docs/user-guide/teacher-workflow.md`：教師完整操作流程（建班→指派→審閱→遊戲化）
- 新建 `docs/user-guide/student-workflow.md`：學生完整操作流程（加入→簽到→提交→排行榜）
- 新建 `docs/architecture.md`：系統架構、模組設計、資料流圖、資料模型
- 新建 `docs/extensions.md`：Extension Registry 擴充套件開發指南
- 新建 `docs/migrations.md`：資料庫 Migration 系統使用說明
- 刪除 `Usage.md`：內容拆散至 `docs/user-guide/` 各文件
- 更新 `pyproject.toml`：版本號升至 0.5.0

## Capabilities

### New Capabilities

(none — 此變更不涉及程式碼功能變動)

### Modified Capabilities

(none)

## Impact

- Affected specs: 無（純文件變更）
- Affected code: `pyproject.toml`（版本號）
- Affected docs:
  - `README.md`（改寫）
  - `CONTRIBUTING.md`（新建）
  - `SECURITY.md`（新建）
  - `CHANGELOG.md`（新建）
  - `docs/getting-started.md`（新建）
  - `docs/configuration.md`（新建）
  - `docs/user-guide/admin-setup.md`（新建）
  - `docs/user-guide/teacher-workflow.md`（新建）
  - `docs/user-guide/student-workflow.md`（新建）
  - `docs/architecture.md`（新建）
  - `docs/extensions.md`（新建）
  - `docs/migrations.md`（新建）
  - `Usage.md`（刪除）
