## Context

徽章管理頁面（`/pages/classes/{class_id}/badges`）目前支援 CRUD 操作，但缺少「查看持有狀態」和「收回」功能。後端已有手動頒發 API (`POST /classes/{class_id}/badges/{badge_id}/award`)，但前端從未實作觸發它的 UI。

現有的 `BadgeAward` model 是純 insert-only 設計，沒有任何撤銷機制。系統其他模組（排行榜、dashboard、觸發器評估）都直接查詢 `BadgeAward` 計數，引入 soft delete 後這些查詢都需要加上 `revoked_at is None` 過濾條件。

安全方面，`security-notes.md` 已記錄 IDOR-001（手動頒發未驗證成員身份，已修復）。新增的 detail 和 revoke endpoint 需遵循相同的防護 pattern。

## Goals / Non-Goals

**Goals:**

- 教師可點擊徽章卡片，查看該徽章的「已獲得」和「未獲得」學生清單
- 教師可從 modal 中對手動徽章執行「頒發」操作
- 教師可對所有類型徽章執行「收回」操作
- 收回採用 soft delete，保留審計軌跡（who + when）
- 所有新端點須防範 IDOR 和越權存取

**Non-Goals:**

- 獨立頁面取代 modal（future work）
- 學生搜尋、過濾、分頁（future work）
- 審計日誌查看介面（future work）
- 批次頒發 / 批次收回
- 已收回徽章的「重新頒發」UI（可透過現有頒發流程達成，因為 soft delete 後該學生會出現在「未獲得」清單）

## Decisions

### Soft delete 欄位設計

在 `BadgeAward` model 新增兩個 optional 欄位：

```python
revoked_at: Optional[datetime] = None
revoked_by: Optional[str] = None  # teacher user_id
```

**為什麼不用硬刪除**：需要審計軌跡，未來可擴展為審計日誌頁面。

**為什麼不用獨立的 revocation log table**：目前規模不需要，兩個欄位足以記錄「誰在何時收回」。未來若需更細緻的審計（例如多次頒發-收回循環），再考慮獨立 table。

### 查詢層面的 soft delete 過濾

所有查詢 `BadgeAward` 的地方都需加上 `BadgeAward.revoked_at == None` 條件。受影響的位置：

| 位置 | 用途 |
|------|------|
| `service.py: award_badge()` | 查重複 award 時需排除已撤銷的 |
| `service.py: get_student_badges()` | 學生徽章列表 |
| `router.py: my_badges` | 學生 API |
| `router.py: badges_manage_page` | 教師管理頁面的 award_count |
| `router.py: class_student_stats` | 學生統計的 badge_count |
| `router.py: delete_badge` | 刪除保護的 award_count |
| `pages/router.py: dashboard_page` | Dashboard 的 badge_count 和 badge_awards |
| `service.py: build_eval_context` | DSL 觸發器的 badge_count |
| `leaderboard/router.py` | 排行榜的 badge_count（如有） |

為降低遺漏風險，新增一個 helper function：

```python
def active_awards_query(*filters):
    """Return BadgeAward query with revoked_at == None pre-applied."""
    return BadgeAward.find(*filters, BadgeAward.revoked_at == None)
```

### Detail API 設計

```
GET /classes/{class_id}/badges/{badge_id}/detail
```

回傳格式：

```json
{
  "badge": { "id", "name", "icon", "description", "trigger_key", "trigger_rule_id" },
  "is_manual": true,
  "awarded": [
    { "award_id", "student_id", "student_name", "awarded_at", "awarded_by", "reason" }
  ],
  "not_awarded": [
    { "student_id", "student_name" }
  ]
}
```

學生清單來源：`ClassMembership.find(class_id=class_id, role="student")`，不接受外部 student_id 參數。`is_manual` 由 `trigger_key is None and trigger_rule_id is None` 判斷，前端據此決定是否顯示「頒發」按鈕。

### Revoke API 設計

```
POST /classes/{class_id}/badges/{badge_id}/revoke
Body: { "award_id": "..." }
```

使用 POST 而非 DELETE，因為這不是硬刪除而是狀態變更。

安全驗證順序：
1. `can_manage_class(teacher, cls)` — 教師是否管理此班級
2. `badge.class_id == class_id` — 徽章是否屬於此班級
3. `award.badge_id == badge_id and award.class_id == class_id` — award 是否屬於此徽章和班級
4. `award.revoked_at is None` — 是否尚未被撤銷

### 重新頒發已撤銷的徽章

`award_badge()` 目前查 existing award 來防重複。加入 soft delete 後，需將查詢改為只查 `revoked_at is None` 的 award。這樣一來，已被收回的學生會出現在「未獲得」清單，教師可以重新頒發（建立新的 BadgeAward record）。歷史的已撤銷 award 會保留為審計紀錄。

### Modal UI 互動設計

- 徽章卡片整行可點擊（加上 `cursor-pointer`）
- 點擊後 fetch detail API，用既有的 `Modal` 系統顯示
- 已獲得區塊：每行顯示學生名稱、獲得時間、「收回」按鈕
- 未獲得區塊：手動徽章每行顯示「頒發」按鈕；自動觸發徽章此區塊隱藏頒發按鈕
- 操作成功後 in-place 更新 modal 內容（重新 fetch detail），不需 reload 整頁
- 操作成功後同步更新卡片上的「N 人獲得」badge

## Risks / Trade-offs

- **[既有查詢遺漏 soft delete 過濾]** → 透過 `active_awards_query` helper 集中管理，減少遺漏。Task 中逐一列出所有需修改的查詢位置。
- **[重新頒發產生多筆歷史 award]** → 這是 by design 的審計特性，不是 bug。每次頒發都是獨立的 award record。
- **[Modal 不支援大量學生]** → 目前規模可接受，搜尋和分頁列為 future work。
- **[Revoke 後觸發器可能重新頒發]** → 自動觸發的徽章被收回後，若學生仍符合觸發條件，下次事件發生時會重新自動頒發。這是預期行為——如果教師想永久阻止，應該修改觸發條件或刪除徽章定義。
