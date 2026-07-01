## 1. OSS 基礎文件（根目錄四大文件 + docs/ 子目錄）

> 文件語言：台灣慣用繁體中文 + 英文專業名詞（首次出現附繁中翻譯）。所有文件均遵循此規範。

- [x] [P] 1.1 新建 `CHANGELOG.md`：採用 Keep a Changelog 格式，回溯 0.1.0–0.3.0 歷史紀錄，新增 0.5.0 區段（分 Added / Changed / Fixed / Security / Removed）
- [x] [P] 1.2 新建 `SECURITY.md`：安全政策、漏洞通報流程、已實施的安全措施摘要

## 2. 部署與設定文件

- [x] [P] 2.1 新建 `docs/getting-started.md`：前置需求、Docker Compose 部署、本機開發環境設定、首次啟動流程
- [x] [P] 2.2 新建 `docs/configuration.md`：所有環境變數完整說明（含新增的 `MONGO_ROOT_PASSWORD`、`REDIS_PASSWORD`）、Docker 服務設定、生產環境注意事項

## 3. 使用者操作指南

- [x] [P] 3.1 新建 `docs/user-guide/admin-setup.md`：系統初始設定精靈操作說明（首次部署後的 Setup Wizard 流程）
- [x] [P] 3.2 新建 `docs/user-guide/teacher-workflow.md`：教師完整操作流程（建班→邀請→指派任務→簽到設定→審閱提交→遊戲化設定→Discord 通知）
- [x] [P] 3.3 新建 `docs/user-guide/student-workflow.md`：學生完整操作流程（加入班級→每日簽到→提交練習→查看點數與徽章→排行榜→社群牆）

## 4. 開發者文件

- [x] [P] 4.1 新建 `docs/architecture.md`：系統架構圖、模組設計、資料流、資料模型摘要、Permission 系統概述
- [x] [P] 4.2 新建 `docs/extensions.md`：Extension Registry 擴充套件開發指南（AuthProvider、RewardProvider、BadgeTrigger、SubmissionValidator Protocol 說明）
- [x] [P] 4.3 新建 `docs/migrations.md`：Migration CLI 使用說明、Migration 檔案格式、撰寫新 Migration 的步驟

## 5. 貢獻指南

- [x] 5.1 新建 `CONTRIBUTING.md`：開發環境設定、專案結構概覽、測試方式、Commit 規範、Spectra 工作流程、PR 流程

## 6. README 改寫與版本更新

- [x] 6.1 改寫 `README.md`：更新功能清單、技術堆疊、快速開始、環境變數表、文件索引連結，版本標示 0.5.0
- [x] 6.2 更新 `pyproject.toml` 版本號跳至 0.5.0
- [x] 6.3 刪除 `Usage.md`（Usage.md 內容遷移後刪除）
