## 1. 資料模型 — Class model 新增 discord_template 欄位

- [x] 1.1 [P] 在 Class model 中使用嵌套 dict 儲存模板欄位而非獨立 collection — 新增 `discord_template` embedded field（含 `title_format`、`description_template`、`footer_text`），滿足 "Class model includes Discord template embedded field" 與 "Class stores Discord message template defaults" 需求
- [x] 1.2 [P] 撰寫 `discord_template` 欄位單元測試 — 驗證新班級 `discord_template` 預設為 `None`、既有班級文件向下相容、學生端不暴露該欄位

## 2. 模板解析引擎 — 變數插值與 fallback

- [x] 2.1 實作 SafeDict 類別，使用 str.format_map() 搭配 SafeDict 實作變數插值 — 支援 `{task_name}`、`{date}`、`{class_name}`、`{description}` 四個變數，滿足 "Template variable interpolation" 需求
- [x] 2.2 實作三層 fallback 解析函式，採用三層 fallback 解析策略（任務覆蓋 > 班級預設 > 系統預設）
- [x] 2.3 實作 Discord embed 欄位長度限制與截斷邏輯（title 256、description 4096、footer 2048），滿足 "Discord embed field length enforcement" 需求
- [x] 2.4 撰寫模板解析引擎單元測試 — 涵蓋正常替換、未定義變數保留原文、大括號語法錯誤 fallback、三層 fallback 優先順序、長度截斷

## 3. API — PATCH 班級模板端點

- [x] 3.1 新增 PATCH API 設定班級模板 — 實作 `PATCH /classes/{class_id}/discord-template` endpoint，滿足 "Teacher sets class Discord template via API" 需求
- [x] 3.2 撰寫 PATCH endpoint 測試 — 驗證權限檢查（403）、部分更新保留既有欄位、空字串清除欄位

## 4. Discord 發送整合 — send_task_embed() 模板驅動

- [x] 4.1 在 send_task_embed() 中整合模板解析邏輯 — 擴充函式簽名加入 optional override 參數，整合 fallback 解析與變數插值，滿足 "Task assignment optionally syncs to Discord" 修改需求
- [x] 4.2 更新任務派發 router 呼叫端，傳入班級模板與任務層級覆蓋參數
- [x] 4.3 撰寫 send_task_embed() 整合測試 — 驗證無模板時行為不變、班級模板生效、任務覆蓋優先、變數正確替換

## 5. 前端 UI — 班級模板設定

- [x] 5.1 [P] 在 class_hub.html 新增 DC 訊息模板設定區，包含 title、description textarea、footer 三個欄位，與 PATCH API 串接
- [x] 5.2 [P] 在 template_assign.html 新增進階選項折疊區，滿足 "Task assignment supports per-task template overrides" 需求 — 預填班級預設值，折疊（collapsed）為預設狀態
- [x] 5.3 實作說明 Modal（Help modal displays available variables and Discord Markdown syntax）— 含可用變數表、Discord Markdown 語法速查、不支援語法警告
