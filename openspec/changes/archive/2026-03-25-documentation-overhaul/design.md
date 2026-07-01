## Context

專案已從 0.1.0 發展至 0.3.0，期間完成核心功能（認證、班級、任務、簽到、遊戲化、社群牆）、安全強化（速率限制、CSRF、Docker 認證）等，但說明文件未同步更新。現有 `README.md` 仍引用已刪除的 `CONTRIBUTE.md`、環境變數表缺少新增的 `MONGO_ROOT_PASSWORD`/`REDIS_PASSWORD`、無安全政策文件、無版本紀錄。

## Goals / Non-Goals

**Goals:**

- 為四種角色（系統管理者、教師、學生、開發者）各提供對應的操作指引
- 所有文件以台灣慣用繁體中文撰寫，專業名詞保留英文（首次出現附繁中翻譯）
- 遵循 OSS 社群慣例：`README.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CHANGELOG.md` 四大基礎文件
- 建立 `docs/` 目錄結構，使文件具備可擴充性
- 回溯 CHANGELOG 至 0.1.0，建立完整版本紀錄
- 版本號升至 0.5.0

**Non-Goals:**

- 不撰寫 API Reference 文件（後續以 FastAPI 內建 Swagger UI 取代）
- 不變更任何程式碼邏輯（僅 `pyproject.toml` 版本號）
- 不翻譯文件為英文版本
- 不新增自動化文件產生工具

## Decisions

### 文件語言：台灣慣用繁體中文 + 英文專業名詞

所有文件以台灣慣用繁體中文書寫。專業技術名詞首次出現時以「英文（繁中翻譯）」格式呈現，後續直接使用英文。嚴禁大陸用語（如「項目」→「專案」、「默認」→「預設」、「代碼」→「程式碼」）。

### 文件結構：根目錄四大文件 + docs/ 子目錄

根目錄放置 OSS 標準文件（README、CONTRIBUTING、SECURITY、CHANGELOG），詳細指引放在 `docs/` 下。`docs/user-guide/` 依角色拆分。此結構參考 GitHub 社群慣例，便於 GitHub 自動識別 SECURITY.md 和 CONTRIBUTING.md。

替代方案：全部放根目錄。缺點：文件數量多時根目錄雜亂。

### Usage.md 內容遷移後刪除

現有 `Usage.md` 的 API 使用範例將拆散至 `docs/user-guide/teacher-workflow.md` 和 `docs/user-guide/student-workflow.md`，完成後刪除 `Usage.md`。`README.md` 中的文件索引會更新指向新位置。

### CHANGELOG 格式：Keep a Changelog

採用 [Keep a Changelog](https://keepachangelog.com/) 格式，分類為 Added、Changed、Fixed、Security、Removed。回溯 0.1.0–0.3.0 的歷史紀錄根據 git commit 歷史整理。

### 版本號跳至 0.5.0

0.3.0 → 0.5.0 跳過 0.4.0，因為中間包含兩個安全修復 change（security-bug-fixes + security-hardening）加上本次文件全面更新，變動幅度足以跳版。

## Risks / Trade-offs

- [文件與程式碼可能脫節] → 文件中避免寫死特定實作細節，以功能描述為主；後續功能變更時同步更新文件
- [CHANGELOG 回溯可能遺漏] → 以 git commit 歷史為依據，按 Spectra change 為單位整理，覆蓋率高
- [文件數量多] → 此結構的每份文件都有明確的讀者和用途，不存在冗餘文件
