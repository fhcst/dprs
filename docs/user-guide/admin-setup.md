# 管理者初始設定與系統管理

> 適用版本：DPRS (Daily Practice & Review System) v0.3.0+

---

## 1. 概述

DPRS 採用 Setup Wizard（設定精靈）機制：系統首次部署完成後，開啟瀏覽器訪問任何頁面都會自動導向設定精靈頁面。管理者須透過此精靈完成初始化，建立站台名稱與第一個管理員帳號，系統才能正式啟用。

設定精靈僅在系統尚未初始化時出現，完成後即永久停用，無法再次進入。

---

## 2. Setup Wizard 流程

### 2.1 自動重新導向

系統啟動時，`SetupGuardMiddleware`（設定守衛中介層）會檢查系統是否已完成初始化。若尚未初始化，所有對 `/setup` 以外路徑的請求，皆會被自動 redirect（重新導向）至 `/setup`。

技術細節：系統透過 Redis flag（旗標）與 MongoDB 中的 `SystemConfig` document（文件）雙重確認初始化狀態。即使 Redis 資料遺失，系統也能從 MongoDB 自動恢復狀態。

### 2.2 填寫初始設定

設定精靈頁面要求填寫以下三個欄位：

| 欄位 | 說明 | 限制 |
|------|------|------|
| Site Name（站台名稱） | 顯示於網站標題與頁面上方 | 必填 |
| Admin Username（管理員帳號） | 初始管理員的登入帳號 | 必填，不可與既有帳號重複 |
| Admin Password（管理員密碼） | 初始管理員的登入密碼 | 必填，最少 8 個字元 |

> **注意：** 此處設定的管理員帳號將擁有 `SITE_ADMIN` 權限，為系統最高權限等級。請務必使用強度足夠的密碼，並妥善保管。

### 2.3 系統初始化動作

送出表單後，系統依序執行：

1. 建立 `SystemConfig` document，儲存站台名稱（admin email 初始為空）
2. 建立管理員 `User` document，授予完整的 `SITE_ADMIN` permission（權限）
3. 於 Redis 寫入設定完成旗標
4. 更新記憶體中的設定狀態與網頁全域 context（上下文）

### 2.4 完成後導向

初始化成功後，系統自動導向至首頁 `/`。由於尚未登入，首頁會再導向至 Login Page（登入頁面）`/pages/login`。請使用方才建立的管理員帳號密碼登入。

> **注意：** Setup Wizard 設有 rate limit（速率限制），每分鐘最多 3 次提交，以防止惡意嘗試。

---

## 3. 系統管理功能

### 3.1 Admin Panel 入口

登入後，具備 `MANAGE_USERS` 或 `WRITE_SYSTEM` permission 的使用者可進入 Admin Panel（管理面板），路徑為：

```
/pages/admin/
```

Admin Panel 總覽頁面顯示以下統計資訊：

- 系統使用者總數
- 進行中的 class（班級）數量
- 已封存的 class 數量

### 3.2 管理面板各區塊

Admin Panel 包含以下管理區塊，各區塊所需權限不同：

| 區塊 | 路徑 | 所需權限 |
|------|------|----------|
| 總覽 | `/pages/admin/` | `MANAGE_USERS` 或 `WRITE_SYSTEM` |
| 使用者管理 | `/pages/admin/users/` | `MANAGE_USERS` |
| 班級管理 | `/pages/admin/classes/` | `MANAGE_ALL_CLASSES` |
| 系統設定 | `/pages/admin/system/` | `WRITE_SYSTEM` |

### 3.3 系統設定

於 `/pages/admin/system/` 可修改以下項目：

- **Site Name（站台名稱）** — 修改後即時反映於所有頁面標題
- **Admin Email（管理員信箱）** — 系統管理者聯絡信箱

修改後點選儲存，系統會同步更新 MongoDB 與記憶體中的設定。

### 3.4 班級管理總覽

於 `/pages/admin/classes/` 可檢視所有班級列表，包含：

- 班級名稱
- 擁有者（教師）
- 邀請碼
- 成員人數
- 是否已封存

> 此頁面需要 `MANAGE_ALL_CLASSES` 權限，屬於 `CLASS_MANAGER` 以上角色才具備。

---

## 4. 使用者管理

### 4.1 手動建立使用者

路徑：`/pages/admin/users/new`

建立使用者時需填寫以下欄位：

| 欄位 | 必填 | 說明 |
|------|------|------|
| Username（帳號） | 是 | 登入用帳號，系統內不可重複 |
| Password（密碼） | 是 | 最少 8 個字元 |
| Display Name（顯示名稱） | 是 | 於介面上顯示的暱稱 |
| Name（真實姓名） | 否 | 僅管理者可修改 |
| Email（電子信箱） | 是 | 使用者的電子信箱 |
| Permissions（權限） | 是 | 透過 preset 或自訂權限矩陣設定 |
| Identity Tags（身分標籤） | 否 | 標註使用者身分類別 |
| Tags（自訂標籤） | 否 | 以逗號分隔的自訂分類標籤 |

若 identity tag 包含 `STUDENT`，額外顯示：

| 欄位 | 說明 |
|------|------|
| Class Name（行政班級） | 例如「302班」 |
| Seat Number（座號） | 班級內座號 |

> **權限限制：** 管理者無法授予高於自身的權限。例如，不具備 `WRITE_SYSTEM` 的管理者無法建立擁有該權限的帳號。

### 4.2 編輯與刪除使用者

- **編輯：** 於使用者列表點選編輯，可修改顯示名稱、真實姓名、信箱、權限、身分標籤、密碼等所有欄位
- **刪除：** 可刪除單一使用者，但不可刪除自己的帳號
- **批次刪除：** 勾選多個使用者後一次刪除（自動排除操作者本人）
- **批次更新權限：** 勾選多個使用者後統一設定權限

### 4.3 CSV Import（CSV 匯入）

路徑：透過 API `POST /admin/users/import` 上傳 CSV 檔案，批次建立使用者帳號。

**下載範本：** 可透過 `GET /admin/users/import/template?type=student` 或 `?type=staff` 下載對應的 CSV 範本。

#### 學生範本欄位

| 欄位名稱 | 說明 | 範例 |
|----------|------|------|
| `username` | 登入帳號 | `s001` |
| `password` | 密碼（最少 8 字元） | `password123` |
| `display_name` | 顯示名稱 | `暱稱` |
| `name` | 真實姓名 | `真實姓名` |
| `email` | 電子信箱 | `student@school.edu` |
| `identity_tag` | 身分標籤 | `student` |
| `preset` | 權限 preset 名稱 | `STUDENT` |
| `tags` | 自訂標籤（以分號分隔） | `tag1;tag2` |
| `class_name` | 行政班級 | `302班` |
| `seat_number` | 座號 | `1` |

#### 教職員範本欄位

| 欄位名稱 | 說明 | 範例 |
|----------|------|------|
| `username` | 登入帳號 | `t001` |
| `password` | 密碼（最少 8 字元） | `password123` |
| `display_name` | 顯示名稱 | `暱稱` |
| `name` | 真實姓名 | `真實姓名` |
| `email` | 電子信箱 | `teacher@school.edu` |
| `identity_tag` | 身分標籤 | `teacher` |
| `preset` | 權限 preset 名稱 | `TEACHER` |
| `tags` | 自訂標籤（以分號分隔） | `tag1;tag2` |

> **檔案限制：** CSV 檔案大小上限為 1 MB，編碼須為 UTF-8（支援 BOM）。匯入結果會回傳成功筆數與失敗明細（含行號與原因）。

### 4.4 Permission Presets（權限預設組合）

系統提供以下 preset，每組對應一個 bitmask（位元遮罩）組合：

| Preset 名稱 | 涵蓋權限 | 適用對象 |
|-------------|---------|---------|
| `STUDENT` | 個人檔案讀寫、提交任務、簽到、查看班級與任務 | 一般學生 |
| `TEACHER` | STUDENT 全部 + 管理自有班級、管理任務、查看使用者 | 教師 |
| `STAFF` | 與 TEACHER 相同 | 行政人員 |
| `CLASS_MANAGER` | TEACHER 全部 + 管理所有班級 | 班級總管理者 |
| `USER_ADMIN` | 個人檔案讀寫 + 使用者管理（讀寫） | 帳號管理員 |
| `SYS_ADMIN` | 個人檔案讀寫 + 系統設定（讀寫） | 系統管理員 |
| `SITE_ADMIN` | TEACHER + 管理所有班級 + 使用者管理 + 系統設定 | 站台最高管理者 |

#### 權限網域明細

系統將權限依 domain（網域）分組，管理者可透過權限矩陣細緻調整：

| Domain | 唯讀權限 | 讀寫權限 |
|--------|---------|---------|
| Self（個人） | 查看個人資料、提交任務、簽到 | + 修改個人資料 |
| Class（班級 - 教師） | 查看班級 | + 建立班級、管理自有班級成員與邀請碼 |
| ClassManager（班級 - 全局管理） | — | 管理系統內所有班級 |
| Task（任務） | 查看任務模板 | + 建立與管理任務模板 |
| User（使用者） | 查看使用者清單 | + 建立、編輯、刪除使用者 |
| System（系統） | 查看系統設定 | + 修改系統設定 |

### 4.5 Identity Tags（身分標籤）

Identity tag 用於標註使用者的身分類別，與 permission 分開管理。系統目前支援以下三種身分標籤：

| 標籤值 | 說明 |
|--------|------|
| `student` | 學生 |
| `teacher` | 教師 |
| `staff` | 行政人員 |

身分標籤的用途：

- 區分使用者身分以利管理與篩選
- 當 identity tag 為 `student` 時，可額外設定 Student Profile（學生檔案），包含行政班級與座號
- CSV 匯入時以此欄位判斷是否需要填寫學生相關欄位

> **提醒：** Identity tag 與 permission preset 是獨立的概念。一個使用者可以持有 `teacher` 身分標籤但僅擁有 `STUDENT` 等級的權限，反之亦然。管理者應確保兩者的搭配合理。
