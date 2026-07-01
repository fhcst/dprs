## Why

教師在自動化發送每日任務到 Discord 時，訊息格式完全 hardcoded，無法自訂。教師需要能自訂訊息模板來配合班級風格、加入激勵標語等。

## What Changes

- Class model 新增 `discord_template` 嵌套欄位（title_format、description_template、footer_text）作為班級預設模板
- 派發任務的進階選項中可覆蓋 title、description、footer
- Description 支援 Discord Markdown + `{variable}` 變數插值（`{task_name}`、`{date}`、`{class_name}`、`{description}`）
- Title 預設格式：`{task_name} — {date}`
- Footer 預設為系統名稱（`site_name`），可自訂標語
- 新增 `(?)` 說明按鈕 → Modal 顯示可用變數列表 + Discord Markdown 語法速查
- `send_task_embed()` 改為根據模板渲染

## Capabilities

### New Capabilities

- `dc-message-template`: Discord 訊息模板系統（模板資料模型、變數插值引擎、Markdown 語法說明 Modal）

### Modified Capabilities

- `discord-webhook`: `send_task_embed()` 從 hardcoded 改為模板驅動渲染
- `class-management`: Class model 新增 `discord_template` 欄位與對應的設定 API

## Impact

- 受影響程式碼：`src/integrations/discord/service.py`、`src/core/classes/models.py`、`src/core/classes/router.py`、`src/core/classes/service.py`
- 受影響 UI：`src/templates/teacher/class_hub.html`（模板設定區）、`src/templates/teacher/template_assign.html`（進階選項）
- 新增 API：`PATCH /classes/{class_id}/discord-template`（設定班級預設模板）
