# Migration 系統

## 概述

DPRS 使用自製的 migration（資料庫遷移）框架，管理 MongoDB 的 schema evolution（結構演進）。

MongoDB 雖然是 schemaless（無固定結構）資料庫，不需要像關聯式資料庫那樣執行 `ALTER TABLE`，但仍有許多操作需要透過 migration 來管理：

- **Index（索引）** 的建立與移除
- **Field rename（欄位更名）** 或格式變更
- **Data transformation（資料轉換）**，例如根據既有欄位推算並填入新欄位

Migration 框架透過 Motor（非同步 MongoDB 驅動程式）直接操作資料庫，並在 `migrations` collection 中追蹤每次執行紀錄，確保每筆 migration 只會被套用一次。

---

## CLI 指令

所有指令皆在專案根目錄下執行，透過 `uv run` 啟動：

### 初始化追蹤 collection

```bash
uv run python scripts/migrate.py init
```

首次部署時執行一次即可。此指令會在資料庫中建立 `migrations` collection 及其所需的 index。

### 套用所有待執行的 migration

```bash
uv run python scripts/migrate.py up
```

依照檔名排序，逐一執行尚未套用的 migration。已套用過的會自動跳過。

### 回滾最後一筆 migration

```bash
uv run python scripts/migrate.py down
```

僅回滾最近一筆已套用的 migration。若需要回滾多筆，請重複執行此指令。

### 查看目前狀態

```bash
uv run python scripts/migrate.py status
```

列出所有 migration 檔案及其狀態（`applied` 或 `pending`）。輸出範例：

```
Status     Migration
------------------------------------------------------------
applied    20260317_001_initial_indexes.py
applied    20260319_002_manage_class_rename.py
applied    20260319_003_init_identity_tags.py
```

---

## Migration 檔案格式

### 命名慣例

檔案放置於 `scripts/migrations/` 目錄下，命名格式為：

```
YYYYMMDD_NNN_description.py
```

| 片段          | 說明                                           |
| ------------- | ---------------------------------------------- |
| `YYYYMMDD`    | 日期，用於排序                                 |
| `NNN`         | 三位數流水號，同一天內區分順序                 |
| `description` | 簡短描述，僅使用小寫英文字母與底線（`_`）      |

範例：

- `20260317_001_initial_indexes.py`
- `20260319_002_manage_class_rename.py`
- `20260319_003_init_identity_tags.py`

### 必要函式

每個 migration 檔案必須定義兩個 async function：

```python
async def forward() -> None:
    """套用此 migration。"""
    ...

async def backward() -> None:
    """回滾此 migration。"""
    ...
```

### 取得資料庫連線

由於 migration 框架不會自動注入資料庫連線，每個檔案需自行建立連線。慣例是定義一個 `_get_db()` helper：

```python
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def _get_db():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "dts2")
    client = AsyncIOMotorClient(mongo_url)
    return client, client[db_name]
```

> **注意**：若 `_get_db()` 回傳 `client`，記得在 `forward()` / `backward()` 結尾呼叫 `client.close()` 以釋放連線。

### 範例：建立 Index

摘自 `20260317_001_initial_indexes.py`：

```python
async def forward() -> None:
    client, db = await _get_db()
    try:
        await db["users"].create_index("username", unique=True)
        await db["users"].create_index("role")
        await db["classmemberships"].create_index(
            [("class_id", 1), ("user_id", 1)], unique=True
        )
        # ... 其餘 index
    finally:
        client.close()

async def backward() -> None:
    client, db = await _get_db()
    try:
        for collection_name in ["users", "classmemberships", ...]:
            await db[collection_name].drop_indexes()
    finally:
        client.close()
```

### 範例：資料轉換

摘自 `20260319_003_init_identity_tags.py`，根據既有的 `permissions` 位元旗標推算 `identity_tags`：

```python
MANAGE_OWN_CLASS = 0x020
SUBMIT_TASK      = 0x004

async def forward(db=None) -> None:
    if db is None:
        db = await _get_db()

    async for doc in db["users"].find(
        {"$or": [{"identity_tags": {"$exists": False}}, {"identity_tags": []}]}
    ):
        perms = doc.get("permissions", 0)
        tags: list[str] = []

        if perms & MANAGE_OWN_CLASS:
            tags.append("teacher")
        elif perms & SUBMIT_TASK:
            tags.append("student")

        if tags:
            await db["users"].update_one(
                {"_id": doc["_id"]},
                {"$set": {"identity_tags": tags}},
            )

async def backward(db=None) -> None:
    if db is None:
        db = await _get_db()
    await db["users"].update_many({}, {"$set": {"identity_tags": []}})
```

### 範例：No-op 記錄性 Migration

當變更僅涉及程式碼層面的重新命名（例如 permission flag 更名），但資料庫中儲存的值不變時，可撰寫 no-op migration 作為變更紀錄：

```python
async def forward(db=None) -> None:
    """No-op: MANAGE_OWN_CLASS 保留與 MANAGE_CLASS 相同的位元值 (0x020)。"""
    pass

async def backward(db=None) -> None:
    """No-op: 原因同 forward。"""
    pass
```

---

## 撰寫新的 Migration

### 步驟

1. **建立檔案**：在 `scripts/migrations/` 目錄下建立新檔案，遵循命名慣例。流水號接續現有最大值：

   ```bash
   # 查看目前最新的流水號
   ls scripts/migrations/
   # 假設最新為 003，則新檔案為：
   touch scripts/migrations/20260325_004_add_some_feature.py
   ```

2. **實作 `forward()` 與 `backward()`**：
   - `forward()` 執行正向操作（建立 index、轉換資料等）
   - `backward()` 必須能完整撤銷 `forward()` 的所有變更

3. **本機測試**：

   ```bash
   # 確認 status 顯示新 migration 為 pending
   uv run python scripts/migrate.py status

   # 套用
   uv run python scripts/migrate.py up

   # 驗證套用結果（視情況查詢資料庫）

   # 回滾
   uv run python scripts/migrate.py down

   # 確認回滾後狀態恢復
   uv run python scripts/migrate.py status

   # 再次套用，確認 idempotent（冪等性）
   uv run python scripts/migrate.py up
   ```

4. **提交程式碼**：確認 forward / backward 雙向測試通過後，將 migration 檔案一併提交至版本控制。

---

## Docker 整合

目前 Docker 容器啟動時**不會**自動執行 migration。部署後需手動進入容器執行：

```bash
# 進入運行中的容器
docker compose exec app bash

# 初始化（首次部署）
uv run python scripts/migrate.py init

# 套用所有待執行的 migration
uv run python scripts/migrate.py up
```

或直接從宿主機（host）執行：

```bash
docker compose exec app uv run python scripts/migrate.py init
docker compose exec app uv run python scripts/migrate.py up
```

> **建議**：未來可將 migration 指令加入 `scripts/docker-entrypoint.sh`，讓容器啟動時自動執行 `migrate.py init` 與 `migrate.py up`，避免部署時遺漏。

---

## 注意事項

1. **務必實作 `backward()`**：即使目前看似不需要回滾，仍應實作完整的 `backward()` 函式。部署出問題時，能快速回滾是關鍵。

2. **部署前雙向測試**：在本機或 staging 環境中，務必測試 `up` 與 `down` 兩個方向，確認資料能正確還原。

3. **Migration 的 idempotency（冪等性）**：盡量讓 `forward()` 可重複執行而不出錯。例如建立 index 時，MongoDB 若偵測到相同 index 已存在會自動忽略；資料轉換則可加上條件篩選（如 `{"identity_tags": {"$exists": False}}`）來避免重複處理。

4. **不要修改已套用的 migration**：一旦某個 migration 已在任何環境中執行過，就不應修改其內容。若需要調整，請撰寫新的 migration。

5. **環境變數**：Migration 透過 `MONGO_URL` 與 `MONGO_DB_NAME` 環境變數連線資料庫。本機開發時預設為 `mongodb://localhost:27017` 與 `dts2`；Docker 環境中由 `docker-compose.yml` 設定。

6. **連線管理**：每個 migration 自行建立與關閉資料庫連線。務必使用 `try/finally` 確保連線在任何情況下都會釋放。
