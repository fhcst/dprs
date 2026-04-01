# Extension Registry 擴充套件註冊系統

## 概述

DPRS 的 Extension Registry（擴充套件註冊表）是一套基於 Python Protocol（協定）的外掛系統，允許開發者以標準化介面替換或擴充核心功能，包含驗證（Authentication）、獎勵（Reward）、徽章（Badge）與提交驗證（Submission Validation）四大類。

所有 Protocol 均標記為 `@runtime_checkable`，在註冊時即進行介面檢查——若實作未滿足 Protocol 定義的方法簽名，會立即拋出 `TypeError`。

**原始碼位置：**

| 模組 | 路徑 |
|------|------|
| Registry 核心 | `src/extensions/registry/core.py` |
| Protocol 定義 | `src/extensions/protocols/` |
| 內建實作 | `src/core/auth/local_provider.py`、`src/gamification/points/providers.py` |
| 註冊進入點 | `src/main.py` → `_register_extensions()` |

---

## Registry API

Extension Registry 以 Module-level Singleton（模組層級單例）方式提供：

```python
from extensions.registry import registry
```

### `registry.register(protocol, key, impl)`

將一個實作（Implementation）註冊至指定的 Protocol 與 Key 之下。

| 參數 | 型別 | 說明 |
|------|------|------|
| `protocol` | `type` | 使用 `@runtime_checkable` 標記的 Protocol 類別 |
| `key` | `str` | 此實作的字串識別碼 |
| `impl` | `Any` | 實作該 Protocol 的物件實例 |

**錯誤處理：** 若 `impl` 未實作 Protocol 所要求的介面，拋出 `TypeError`。

```python
from extensions.protocols.auth import AuthProvider
from core.auth.local_provider import LocalAuthProvider

registry.register(AuthProvider, "local", LocalAuthProvider())
```

### `registry.get(protocol, key)`

依據 Protocol 與 Key 取得已註冊的實作。

| 參數 | 型別 | 說明 |
|------|------|------|
| `protocol` | `type` | Protocol 類別 |
| `key` | `str` | 註冊時使用的字串識別碼 |

**回傳值：** 已註冊的實作物件。

**錯誤處理：** 若找不到對應的實作，拋出 `KeyError`。

```python
provider = registry.get(AuthProvider, "local")
user = await provider.authenticate({"username": "alice", "password": "s3cret"})
```

### `registry.get_all(protocol)`

取得某個 Protocol 下所有已註冊的實作，以 `list` 回傳。

| 參數 | 型別 | 說明 |
|------|------|------|
| `protocol` | `type` | Protocol 類別 |

**回傳值：** `list[Any]` — 所有已註冊的實作物件。若無任何註冊則回傳空串列。

```python
from extensions.protocols.reward import RewardProvider

providers = registry.get_all(RewardProvider)
for provider in providers:
    result = await provider.award(event)
```

---

## 可用的 Protocol（協定）

### AuthProvider — 驗證提供者

定義驗證後端的介面，用於處理使用者身份驗證。

**路徑：** `src/extensions/protocols/auth.py`

**方法：**

```python
async def authenticate(self, credentials: dict[str, Any]) -> User
```

| 參數 | 說明 |
|------|------|
| `credentials` | 依提供者不同而異的憑證字典。本地驗證為 `{"username": str, "password": str}`；OAuth 為 `{"token": str, "provider": str}` |

**回傳值：** 驗證成功時回傳 `User` 文件。

**例外：** 驗證失敗時拋出 `ValueError`。

**內建實作：**

| Key | 類別 | 說明 |
|-----|------|------|
| `"local"` | `LocalAuthProvider` | 使用 bcrypt 雜湊驗證存於 MongoDB 的帳號密碼。內含 Timing Attack（計時攻擊）防護（CWE-208） |

**適用情境：** OAuth 2.0、SAML、SSO（單一登入）、LDAP 等第三方驗證整合。

---

### RewardProvider — 獎勵提供者

定義積分發放邏輯的介面。同一事件觸發時，所有已註冊的 RewardProvider 均會被呼叫。

**路徑：** `src/extensions/protocols/reward.py`

**方法：**

```python
async def award(self, event: RewardEvent) -> PointTransaction | None
```

| 參數 | 說明 |
|------|------|
| `event` | `RewardEvent` 資料類別，包含事件類型與相關資訊 |

**回傳值：** 若有發放積分則回傳 `PointTransaction`，否則回傳 `None`。

**RewardEvent 資料結構：**

```python
@dataclass
class RewardEvent:
    event_type: RewardEventType  # CHECKIN | SUBMISSION | MANUAL
    student_id: str
    class_id: str
    source_id: str               # 簽到紀錄 ID 或提交 ID
    occurred_at: datetime        # 預設為 UTC 當前時間
```

**RewardEventType 事件類型：**

| 列舉值 | 說明 |
|--------|------|
| `CHECKIN` | 學生簽到 |
| `SUBMISSION` | 學生提交作業 |
| `MANUAL` | 教師手動發放 |

**內建實作：**

| Key | 類別 | 說明 |
|-----|------|------|
| `"checkin"` | `CheckinRewardProvider` | 簽到時發放積分（預設 5 點，可透過 `ClassPointConfig` 設定） |
| `"submission"` | `SubmissionRewardProvider` | 提交作業時發放積分（預設 10 點，可透過 `ClassPointConfig` 設定） |

---

### BadgeTrigger — 徽章觸發條件

定義徽章獎勵條件的介面。每次 RewardEvent 發生後，所有已註冊的 BadgeTrigger 均會被評估。

**路徑：** `src/extensions/protocols/badge.py`

**方法：**

```python
async def evaluate(
    self,
    student_id: str,
    event: RewardEvent,
    context: TriggerContext,
) -> bool
```

| 參數 | 說明 |
|------|------|
| `student_id` | 待評估的學生 ID |
| `event` | 觸發評估的 `RewardEvent` |
| `context` | `TriggerContext` 資料類別，攜帶 `class_id` 與 `extra` 擴充欄位 |

**回傳值：** `True` 表示條件達成、應授予徽章；`False` 表示條件未達。

**TriggerContext 資料結構：**

```python
@dataclass
class TriggerContext:
    class_id: str
    extra: dict[str, Any]  # 預設為空字典
```

---

### SubmissionValidator — 提交驗證器

定義作業提交前的自訂驗證邏輯。所有已註冊的 SubmissionValidator 均會在儲存前執行，任何一個回傳 `valid=False` 即拒絕該次提交。

**路徑：** `src/extensions/protocols/validator.py`

**方法：**

```python
async def validate(
    self,
    submission_data: dict[str, Any],
    template: Any,
) -> ValidationResult
```

| 參數 | 說明 |
|------|------|
| `submission_data` | 欄位名稱對應提交值的字典 |
| `template` | 此次提交所對應的 `TaskTemplate` 文件 |

**回傳值：** `ValidationResult` 資料類別。

**ValidationResult 資料結構：**

```python
@dataclass
class ValidationResult:
    valid: bool
    error_message: str = ""  # valid=False 時的錯誤訊息
```

---

## 撰寫自訂 Extension

以下以建立一個「手動加分」的 RewardProvider 為範例，說明完整步驟。

### 步驟一：建立實作類別

在適當的模組中建立一個符合 Protocol 介面的類別。不需顯式繼承 Protocol——只要方法簽名（Method Signature）一致即可，Python 的 Structural Subtyping（結構性子型別）會自動判定。

```python
# src/gamification/points/manual_provider.py

from extensions.protocols.reward import RewardEvent, RewardEventType
from gamification.points.models import PointTransaction
from gamification.points.service import award_points


class ManualRewardProvider:
    """教師手動加分的獎勵提供者。"""

    async def award(self, event: RewardEvent) -> PointTransaction | None:
        if event.event_type != RewardEventType.MANUAL:
            return None

        return await award_points(
            student_id=event.student_id,
            class_id=event.class_id,
            amount=20,  # 手動加分固定 20 點
            source_event="manual",
            source_id=event.source_id,
        )
```

### 步驟二：在 `_register_extensions()` 中註冊

開啟 `src/main.py`，在 `_register_extensions()` 函式中加入註冊呼叫：

```python
def _register_extensions():
    from extensions.registry import registry
    from extensions.protocols.auth import AuthProvider
    from extensions.protocols.reward import RewardProvider
    from core.auth.local_provider import LocalAuthProvider
    from gamification.points.providers import CheckinRewardProvider, SubmissionRewardProvider
    from gamification.points.manual_provider import ManualRewardProvider  # 新增

    registry.register(AuthProvider, "local", LocalAuthProvider())
    registry.register(RewardProvider, "checkin", CheckinRewardProvider())
    registry.register(RewardProvider, "submission", SubmissionRewardProvider())
    registry.register(RewardProvider, "manual", ManualRewardProvider())  # 新增
```

### 步驟三：驗證註冊

應用程式啟動後，可透過 `registry.get()` 確認註冊是否成功：

```python
from extensions.registry import registry
from extensions.protocols.reward import RewardProvider

provider = registry.get(RewardProvider, "manual")
# 若未拋出 KeyError，表示註冊成功
```

---

## 測試

Extension Registry 提供 `TestRegistry` Context Manager（情境管理器），用於在測試中隔離 Registry 狀態，避免測試之間互相影響。

### 使用方式

```python
from extensions.registry.core import TestRegistry
from extensions.protocols.auth import AuthProvider


class MockAuthProvider:
    async def authenticate(self, credentials):
        return {"id": "test-user", "username": "mock"}


def test_custom_auth():
    with TestRegistry() as test_reg:
        test_reg.register(AuthProvider, "mock", MockAuthProvider())
        provider = test_reg.get(AuthProvider, "mock")
        # ... 執行測試邏輯 ...

    # 離開 with 區塊後，原始的 registry singleton 自動還原
```

### 運作原理

1. 進入 `with` 區塊時，`TestRegistry` 建立一個全新的 `ExtensionRegistry` 實例，並取代模組層級的 `registry` singleton。
2. 測試程式碼使用回傳的 `test_reg` 進行註冊與查詢，與正式環境完全隔離。
3. 離開 `with` 區塊後，原始的 singleton 自動恢復，不影響後續測試或應用程式狀態。

---

## DSL 觸發規則與 Code Trigger 共存

`BadgeDefinition` 支援三種觸發來源：

| 欄位 | 來源 | 說明 |
|------|------|------|
| `trigger_key` | ExtensionRegistry 程式碼觸發器 | 對應 `BadgeTrigger` Protocol 的已註冊實作 |
| `trigger_rule_id` | DSL 規則 | 對應 `TriggerRule` 文件中的 DSL 表達式 |
| 都不設 | 手動頒發 | 由教師或管理員透過 API 手動授予 |

`trigger_key` 和 `trigger_rule_id` **互斥**——同一個 `BadgeDefinition` 不可同時設定兩者。此約束由 Pydantic `model_validator` 驗證，若同時提供兩個欄位會拋出 `ValueError`。

### 合併評估流程

`evaluate_triggers_for_event()` 在每次 `RewardEvent` 發生時同時評估 Code Trigger 與 DSL Rule：

```
evaluate_triggers_for_event()
├── Path 1: Code Triggers (ExtensionRegistry)
│   for key, trigger in registry.get_all(BadgeTrigger).items():
│       trigger.evaluate(student_id, event, context)
│
└── Path 2: DSL Rules (Rust engine via PyO3)
    for badge with trigger_rule_id:
        rule = TriggerRule.get(trigger_rule_id)
        dsl_engine.evaluate(rule.expression, eval_context)
```

- **Path 1** 遍歷所有透過 `ExtensionRegistry` 註冊的 `BadgeTrigger` 實作，逐一呼叫 `evaluate()` 方法。
- **Path 2** 查詢所有設有 `trigger_rule_id` 的 `BadgeDefinition`，取出對應的 `TriggerRule`，並透過 PyO3 呼叫 Rust DSL 引擎 `dsl_engine.evaluate()` 進行評估。

開發者仍可使用 Python Protocol 撰寫自訂觸發器並透過 `registry.register(BadgeTrigger, ...)` 註冊——DSL 系統不取代既有的 Code Trigger 機制，兩者共存互補。

---

### `ensure_membership()` — 原子性成員建立

**路徑：** `src/core/classes/service.py`

`ensure_membership()` 使用 MongoDB 的 atomic `update_one` 搭配 `upsert=True` 與 `$setOnInsert` 運算子，以單一操作確保 `ClassMembership` 文件存在：

- 若文件**不存在**：插入新文件，欄位值由 `$setOnInsert` 決定。
- 若文件**已存在**：不做任何修改，直接回傳。

**適用場景：**

- Join-request approval（加入申請核准）
- Batch invite（批次邀請）
- 任何需要確保 `ClassMembership` 存在的流程

此方法取代了先前的 check-then-insert 模式（先查詢是否存在、再決定是否插入），消除了並行請求下的 race condition。在高併發情境中，多個請求同時對同一學生執行 `ensure_membership()` 時，只有第一個會實際插入文件，其餘請求因 `upsert` 語義而安全地跳過寫入。
