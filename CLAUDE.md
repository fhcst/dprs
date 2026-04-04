<!-- SPECTRA:START v1.0.1 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `openspec/specs/`, change proposals in `openspec/changes/`.

## Use `/spectra:*` skills when:

- A discussion needs structure before coding → `/spectra:discuss`
- User wants to plan, propose, or design a change → `/spectra:propose`
- Tasks are ready to implement → `/spectra:apply`
- There's an in-progress change to continue → `/spectra:ingest`
- User asks about specs or how something works → `/spectra:ask`
- Implementation is done → `/spectra:archive`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra:apply` and `/spectra:ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->

# Security Development Notes

修改以下模組前，請先查閱 `docs/security-notes.md`：

- **Badge 系統** (`src/gamification/badges/`) — IDOR 已修復，手動頒發端點已加入 student membership 驗證
- **模板渲染** — 永遠不要對使用者輸入內容使用 `| safe` filter，Markdown 內容若需前端渲染必須搭配 DOMPurify
- **CSRF** — JSON API 依賴 CORS preflight + SameSite cookie 防護，不要變更 cookie SameSite 設定而未重新評估 CSRF 策略
