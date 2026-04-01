## Summary

更新全部 OSS 專案文件，反映 `achievement-dsl` 和 `fix-codex-review-findings` 兩個 change 引入的重大變更。

## Motivation

專案文件落後程式碼兩個 commit，新功能包括：Rust DSL 引擎（WASM + PyO3）、觸發規則管理系統、Multi-stage Dockerfile、ClassMembership unique index、新 API endpoints、CodeMirror 6 + Milkdown 前端編輯器。開發者和部署者無法從現有文件了解這些變更。

## Proposed Solution

更新以下 7 個文件：

1. **README.md** — 技術堆疊新增 Rust/WASM/PyO3、功能特色新增 DSL 觸發規則系統、快速開始新增 Rust 相關說明
2. **CHANGELOG.md** — 新增 v0.6.0 版本紀錄，涵蓋 DSL 引擎、觸發規則管理、前端編輯器、安全性修正、Dockerfile multi-stage build
3. **CONTRIBUTING.md** — 新增 Rust crate 開發流程（toolchain 安裝、wasm-pack build、maturin develop）、專案結構更新含 `crates/dsl-engine/`
4. **SECURITY.md** — 新增 DSL 沙箱安全模型、WASM 隔離、觸發規則驗證、Rich text editor XSS 防護
5. **docs/architecture.md** — 新增 DSL 引擎架構圖、Rust/Python FFI 層、觸發規則評估流程、ClassMembership unique index
6. **docs/extensions.md** — 新增 DSL 觸發規則與 code trigger 共存模型、`ensure_membership()` API
7. **docs/getting-started.md** — 前置需求新增 Rust toolchain（可選）、本機開發新增 DSL 引擎建置步驟

## Non-Goals

- 不更新 `docs/configuration.md` — 目前沒有新增 DSL 相關環境變數（DSL 引擎不需要額外設定）
- 不更新 `docs/migrations.md` — ClassMembership unique index 由 Beanie init_beanie 自動建立
- 不新增獨立的 DSL 使用者指南 — Help Modal 已內建於 UI 中

## Impact

- 受影響檔案：
  - `README.md`
  - `CHANGELOG.md`
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `docs/architecture.md`
  - `docs/extensions.md`
  - `docs/getting-started.md`
