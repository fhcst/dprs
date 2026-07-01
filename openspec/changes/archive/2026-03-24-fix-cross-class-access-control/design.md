## Context

系統的班級範圍授權目前依賴兩種模式：(1) 端點路徑包含 `class_id` 時，handler 內部呼叫 `can_manage_class(user, cls)` 驗證；(2) 端點路徑僅包含資源 ID（如 `template_id`、`submission_id`、`post_id`）時，僅以全域 `require_permission()` 檢查，未回溯資源所屬班級進行驗證。

三組受影響端點均屬模式 (2)：模板 CRUD、提交審查、動態貼文刪除。

## Goals / Non-Goals

**Goals:**

- 為三組受影響端點加入班級範圍授權檢查
- 確保 `MANAGE_ALL_CLASSES` 權限的管理員不受影響
- 新增對應測試驗證跨班級存取被正確拒絕

**Non-Goals:**

- 重構為通用的 class-scoped middleware（改動範圍太大，目前逐端點修補即可）
- 修改端點 URL 結構（如將 `/templates/{id}` 改為 `/classes/{class_id}/templates/{id}`）

## Decisions

### 在 handler 內部加入 can_manage_class 檢查

對每個受影響端點，載入資源後從中取得 `class_id`，接著呼叫 `can_manage_class(user, cls)` 驗證。這與現有 class router 的模式一致（如 `_require_manage()`）。

**替代方案：** 建立通用 decorator 或 middleware 自動從資源推導 `class_id` 並驗證。放棄原因：不同資源的 `class_id` 取得方式不同（template 直接有 `class_id`，submission 也有，post 也有），通用化帶來的抽象收益有限，且增加認知成本。

### 模板端點：從 TaskTemplate 取得 class_id

`update_template`、`delete_template`、`archive_template`、`unarchive_template` 四個端點在 service 層呼叫前，先讀取 `TaskTemplate.get(template_id)`，取得 `class_id`，再驗證。

### 提交審查端點：從 TaskSubmission 取得 class_id

`approve`、`reject`、`comment` 三個端點已有 `sub = await TaskSubmission.get(submission_id)`，只需補上 `can_manage_class` 檢查。

### 動態貼文刪除：從 FeedPost 取得 class_id

`delete post` 端點已有 `post = await FeedPost.get(post_id)`，只需在教師路徑補上班級驗證。

## Risks / Trade-offs

- **[額外 DB 查詢]** → 模板端點需多一次 `Class.get(class_id)`。緩解：查詢量極小，單一文件查詢。
- **[測試覆蓋]** → 需為每組端點新增跨班級拒絕測試。這是必要的安全保障。
