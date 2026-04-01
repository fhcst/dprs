# DPRS 系統架構文件

> **Daily Practice Report System（每日練習報告系統）** v0.3.0

---

## 1. 系統概覽

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client（用戶端）                          │
│              Browser ──── HTML / HTMX / Fetch API               │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼──────────────────────────────────┐
│                     FastAPI Application                          │
│                                                                  │
│  ┌────────────────── Middleware Stack ─────────────────────┐     │
│  │  SetupGuard → CSRF → Session → Rate Limiter            │     │
│  └────────────────────────────────────────────────────────-┘     │
│                               │                                  │
│  ┌────────────────────────────▼──────────────────────────┐      │
│  │                      Routers                           │      │
│  │  auth · users · classes · system · templates ·         │      │
│  │  submissions · checkin · points · badges ·             │      │
│  │  leaderboard · prizes · feed · pages                   │      │
│  └────────────────────────────┬──────────────────────────┘      │
│                               │                                  │
│  ┌────────────────────────────▼──────────────────────────┐      │
│  │               Services / Providers                     │      │
│  │  can_manage_class() · RewardProvider · AuthProvider ·  │      │
│  │  BadgeTrigger · SubmissionValidator                    │      │
│  └──────────┬─────────────────────────────┬──────────────┘      │
│             │                             │                      │
│  ┌──────────▼──────────┐      ┌───────────▼─────────────┐      │
│  │  Beanie ODM         │      │  Redis                   │      │
│  │  (Document Models)  │      │  (Session / State)       │      │
│  └──────────┬──────────┘      └───────────┬─────────────┘      │
└─────────────┼─────────────────────────────┼─────────────────────┘
              │                             │
   ┌──────────▼──────────┐      ┌───────────▼─────────────┐
   │     MongoDB          │      │     Redis Server         │
   └─────────────────────┘      └─────────────────────────┘
```

**請求流程（Request Flow）：**

1. 用戶端發出 HTTP 請求。
2. 請求依序通過 Middleware Stack（中介層堆疊）：SetupGuard → CSRF → Session → Rate Limiter。
3. Router（路由器）根據路徑分派至對應的 Handler（處理器）。
4. Handler 透過 FastAPI Dependency Injection（依賴注入）取得認證使用者與授權檢查。
5. Service Layer（服務層）執行商業邏輯，透過 Beanie ODM 存取 MongoDB，透過 Redis 管理 Session（工作階段）與應用程式狀態。

### DSL Engine 架構

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ CodeMirror 6 │  │  Milkdown    │                 │
│  │ DSL Editor   │  │  WYSIWYG     │                 │
│  └──────┬───────┘  └──────────────┘                 │
│         │ validate/complete/hover                    │
│  ┌──────▼───────┐                                   │
│  │ dsl-engine   │                                   │
│  │ (WASM)       │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
                    │ HTTP API
┌─────────────────────────────────────────────────────┐
│  FastAPI Server                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ triggers/    │  │ badges/      │                 │
│  │ router.py    │  │ service.py   │                 │
│  └──────┬───────┘  └──────┬───────┘                 │
│         │                 │ evaluate                 │
│  ┌──────▼─────────────────▼───────┐                 │
│  │     dsl-engine (PyO3)          │                 │
│  └────────────────────────────────┘                 │
└─────────────────────────────────────────────────────┘
```

---

## 2. 模組結構

```
src/
├── main.py                    # 應用程式進入點：Lifespan、Middleware、Router 註冊
├── core/                      # 核心功能
│   ├── auth/                  #   認證與授權
│   │   ├── deps.py            #     FastAPI 依賴：get_current_user
│   │   ├── guards.py          #     路由守衛：require_permission()
│   │   ├── jwt.py             #     JWT Token 簽發與驗證
│   │   ├── local_provider.py  #     本地帳號密碼認證 Provider
│   │   ├── password.py        #     密碼雜湊（bcrypt）
│   │   ├── permissions.py     #     Permission IntFlag 與 Role Preset
│   │   └── router.py          #     登入、登出、Token 相關端點
│   ├── users/                 #   使用者管理
│   │   ├── models.py          #     User Document
│   │   └── router.py          #     使用者 CRUD 端點
│   ├── classes/               #   班級管理
│   │   ├── models.py          #     Class、ClassMembership Document
│   │   ├── service.py         #     can_manage_class()、邀請碼、加入班級等
│   │   └── router.py          #     班級 CRUD 與成員管理端點
│   └── system/                #   系統設定
│       ├── models.py          #     SystemConfig Document
│       ├── startup.py         #     Redis 狀態初始化、Setup 狀態檢查
│       └── router.py          #     系統設定、初始化設定（Setup Wizard）
├── tasks/                     # 任務領域
│   ├── templates/             #   任務模板
│   │   ├── models.py          #     TaskTemplate、TaskAssignment、TaskScheduleRule
│   │   ├── service.py         #     模板 CRUD、排程邏輯
│   │   └── router.py          #     模板管理端點
│   ├── submissions/           #   繳交紀錄
│   │   ├── models.py          #     TaskSubmission（含審查狀態）
│   │   ├── service.py         #     繳交、審查、重新繳交
│   │   └── router.py          #     繳交與審查端點
│   └── checkin/               #   打卡（出席）
│       ├── models.py          #     CheckinConfig、CheckinRecord、AttendanceCorrection
│       ├── service.py         #     打卡邏輯、出席補正
│       └── router.py          #     打卡端點
├── gamification/              # 遊戲化機制
│   ├── points/                #   點數系統
│   │   ├── models.py          #     PointTransaction、ClassPointConfig
│   │   ├── providers.py       #     CheckinRewardProvider、SubmissionRewardProvider
│   │   ├── service.py         #     點數計算與交易服務
│   │   └── router.py          #     點數查詢與管理端點
│   ├── badges/                #   徽章系統
│   │   ├── models.py          #     BadgeDefinition、BadgeAward
│   │   ├── triggers.py        #     徽章觸發條件
│   │   ├── service.py         #     徽章頒發服務
│   │   └── router.py          #     徽章管理端點
│   ├── leaderboard/           #   排行榜
│   │   └── router.py          #     排行榜查詢端點
│   ├── triggers/               #   觸發規則管理
│   │   ├── models.py           #     TriggerRule Document
│   │   ├── service.py          #     觸發規則 CRUD + CBAC 權限
│   │   └── router.py           #     觸發規則管理端點
│   └── prizes/                #   獎品商城
│       ├── models.py          #     Prize Document
│       └── router.py          #     獎品管理端點
├── community/                 # 社群功能
│   └── feed/                  #   班級動態牆
│       ├── models.py          #     FeedPost、Reaction
│       └── router.py          #     動態牆端點
├── extensions/                # 擴充系統
│   ├── protocols/             #   Protocol 介面定義
│   │   ├── auth.py            #     AuthProvider Protocol
│   │   ├── reward.py          #     RewardProvider Protocol
│   │   ├── badge.py           #     BadgeTrigger Protocol
│   │   └── validator.py       #     SubmissionValidator Protocol
│   ├── registry/              #   擴充註冊中心
│   │   └── core.py            #     ExtensionRegistry singleton
│   └── deps.py               #   擴充相關 FastAPI 依賴
├── integrations/              # 外部整合
│   └── discord/               #   Discord Webhook 整合
├── pages/                     # 網頁 UI 路由
│   ├── router.py              #     SSR 頁面路由（Dashboard、班級頁等）
│   └── deps.py               #     頁面用依賴
├── shared/                    # 共用基礎設施
│   ├── database.py            #     MongoDB 連線（Motor Client）與 Beanie 初始化
│   ├── redis.py               #     Redis 連線
│   ├── csrf.py                #     CSRF Middleware
│   ├── limiter.py             #     Rate Limiter（SlowAPI）
│   ├── sessions.py            #     Session Middleware
│   ├── webpage.py             #     FastAPI-WebPage 模板引擎
│   ├── page_context.py        #     頁面共用 Context
│   └── gravatar.py            #     Gravatar 頭像 URL 產生
└── templates/                 # Jinja2 HTML 模板
    ├── login.html
    ├── setup.html
    ├── settings.html
    ├── shared/                #   共用版面（Layout）
    ├── admin/                 #   管理介面頁面
    ├── teacher/               #   教師介面頁面
    ├── student/               #   學生介面頁面
    └── community/             #   社群頁面

crates/
└── dsl-engine/                # Rust DSL 表達式引擎
    #   pest parser → AST → evaluate/validate/complete/hover/describe/help
```

---

## 3. Middleware 堆疊

Middleware（中介層）以 LIFO（Last In, First Out）順序執行。在 `main.py` 中的註冊順序與實際執行順序如下：

| 註冊順序 | Middleware | 實際執行順序 | 說明 |
|:-:|---|:-:|---|
| 3 | `SetupGuardMiddleware` | 1 (最先) | 系統未完成初始設定時，將所有請求重導至 `/setup` |
| 2 | `CSRFMiddleware` | 2 | 驗證 POST/PUT/DELETE 請求的 CSRF Token |
| 1 | `SessionMiddleware` | 3 | 管理 Cookie-based Session（工作階段） |
| -- | `SlowAPI (Rate Limiter)` | 4 (最後) | 透過 `@limiter.limit()` Decorator（裝飾器）控制請求速率 |

> **注意：** FastAPI/Starlette 的 `add_middleware()` 採用堆疊式設計，**最後加入的最先執行**。SlowAPI 則透過 Exception Handler（例外處理器）掛載，作用於路由層。

---

## 4. 認證與授權

### 4.1 JWT 認證

系統使用 **JWT（JSON Web Token）** 儲存於 **httpOnly Cookie** 中：

```
登入成功 → 簽發 JWT → Set-Cookie: access_token=<jwt>; HttpOnly; Secure
每次請求 → 從 Cookie 取出 access_token → 解碼驗證 → 查詢 User Document
```

- Token Payload（負載）包含 `user_id`，用於查詢使用者。
- `get_current_user()` 是核心依賴，驗證 Token 有效性並回傳 `User` 物件。
- Token 無效或過期時回傳 HTTP 401 Unauthorized（未授權）。

### 4.2 Permission IntFlag（權限位元旗標）

權限系統基於 Python `IntFlag`，每項權限佔據一個 bit（位元）。使用者的 `permissions` 欄位以整數儲存，透過 bitwise AND（位元 AND 運算）檢查權限。

```
Bit 位置      Hex       Permission（權限）          說明
──────────────────────────────────────────────────────────────
bit  0       0x001     READ_OWN_PROFILE           讀取個人資料
bit  1       0x002     WRITE_OWN_PROFILE          修改個人資料
bit  2       0x004     SUBMIT_TASK                繳交任務
bit  3       0x008     CHECKIN                    打卡
bit  4       0x010     READ_CLASS                 查看班級
bit  5       0x020     MANAGE_OWN_CLASS           管理自己的班級
bit  6       0x040     READ_TASKS                 查看任務
bit  7       0x080     MANAGE_TASKS               管理任務
bit  8       0x100     READ_USERS                 查看使用者清單
bit  9       0x200     MANAGE_USERS               管理使用者
bit 10       0x400     READ_SYSTEM                查看系統設定
bit 11       0x800     WRITE_SYSTEM               修改系統設定
bit 12       0x1000    MANAGE_ALL_CLASSES         管理所有班級（全局）
```

**檢查方式：**

```python
# 檢查使用者是否擁有 MANAGE_TASKS 權限
if user.permissions & Permission.MANAGE_TASKS:
    ...  # 允許操作
```

### 4.3 Role Presets（角色預設組合）

角色為預定義的權限組合，**不存入資料庫**——資料庫僅儲存 `permissions` 整數值。管理者透過 Admin UI 可以選用預設角色或自訂組合。

| 角色 | 權限值 | 說明 |
|---|---|---|
| `STUDENT` | `0x05F` | 個人資料讀寫 + 繳交任務 + 打卡 + 查看班級與任務 |
| `TEACHER` | `0x1FF` | STUDENT 全部 + 管理自己班級 + 管理任務 + 查看使用者 |
| `STAFF` | `0x1FF` | 與 TEACHER 相同 |
| `CLASS_MANAGER` | `0x11FF` | TEACHER + 管理所有班級 |
| `USER_ADMIN` | `0x303` | 個人資料讀寫 + 使用者管理 |
| `SYS_ADMIN` | `0xC03` | 個人資料讀寫 + 系統設定管理 |
| `SITE_ADMIN` | `0x1FFF` | TEACHER + 管理所有班級 + 使用者管理 + 系統管理（完整權限） |

### 4.4 Class-Scoped Authorization（班級範圍授權）

除了全局權限旗標，班級相關操作還需通過 `can_manage_class()` 的範圍授權檢查：

```
can_manage_class(user, cls):
    ├── 使用者持有 MANAGE_ALL_CLASSES？ → 允許（全局管理者）
    ├── 使用者持有 MANAGE_OWN_CLASS？
    │   └── 查詢 ClassMembership：該使用者是否為此班級的 teacher？
    │       ├── 是 → 允許
    │       └── 否 → 拒絕
    └── 否 → 拒絕
```

此設計防範 **CWE-639（Insecure Direct Object Reference，不安全的直接物件參照）** 與 **CWE-863（Incorrect Authorization，不正確的授權）**——即使使用者持有教師權限，也無法跨班級存取其他教師的班級資源。

路由守衛 `require_permission()` 作為 FastAPI Dependency（依賴），在路由層進行全局權限過濾；`can_manage_class()` 則在 Service Layer（服務層）進行班級範圍的細粒度授權。

---

## 5. 資料模型摘要

### 5.1 Model 關聯圖

```
User
 │
 ├──1:N──→ ClassMembership ←──N:1── Class
 │              (user_id, class_id, role)
 │
 ├──1:N──→ TaskSubmission ──→ TaskTemplate
 │           (student_id)       (template_id)
 │                                  │
 │                                  ├──1:N──→ TaskAssignment
 │                                  └──1:N──→ TaskScheduleRule
 │
 ├──1:N──→ CheckinRecord
 │           (student_id, class_id)
 │
 ├──1:N──→ PointTransaction
 │           (student_id, class_id)
 │
 ├──1:N──→ BadgeAward ──→ BadgeDefinition
 │           (student_id)     (class_id)
 │
 ├──1:N──→ FeedPost ──→ TaskSubmission
 │           (student_id)   (submission_id)
 │
 └──1:N──→ Reaction
              (user_id, post_id → FeedPost)

Class
 ├──1:N──→ ClassMembership
 │           unique compound index: (class_id, user_id)
 ├──1:N──→ TaskTemplate (class_id)
 ├──1:N──→ CheckinConfig (class_id)
 ├──1:N──→ DailyCheckinOverride (class_id)
 ├──1:N──→ ClassPointConfig (class_id)
 ├──1:N──→ BadgeDefinition (class_id)
 │           trigger_rule_id: Optional[str]，與 trigger_key 互斥（model_validator）
 ├──1:N──→ TriggerRule (class_id)
 ├──1:N──→ Prize (class_id)
 └──1:N──→ AttendanceCorrection (class_id)

SystemConfig ── 單例文件（Singleton Document）
```

### 5.2 Document Model 一覽表

| 模組 | Document | Collection 名稱 | 說明 |
|---|---|---|---|
| core/users | `User` | `users` | 使用者帳號、權限、身分標籤 |
| core/classes | `Class` | `classes` | 班級資訊、邀請碼、可見性 |
| core/classes | `ClassMembership` | `classmemberships` | 使用者與班級的成員關係（student / teacher） |
| core/system | `SystemConfig` | `system_config` | 系統設定（站名、管理者信箱）—— 單例 |
| tasks/templates | `TaskTemplate` | `tasktemplates` | 任務模板：名稱、自訂欄位定義 |
| tasks/templates | `TaskAssignment` | `taskassignments` | 任務指派：模板 + 班級 + 日期 |
| tasks/templates | `TaskScheduleRule` | `taskschedulerules` | 排程規則（單次 / 範圍 / 開放） |
| tasks/submissions | `TaskSubmission` | `tasksubmissions` | 學生繳交紀錄與審查狀態 |
| tasks/checkin | `CheckinConfig` | `checkinconfigs` | 班級打卡設定（時段、星期） |
| tasks/checkin | `DailyCheckinOverride` | `dailycheckinoverrides` | 單日打卡設定覆寫 |
| tasks/checkin | `CheckinRecord` | `checkinrecords` | 學生打卡紀錄 |
| tasks/checkin | `AttendanceCorrection` | `attendancecorrections` | 教師出席補正（遲到 / 缺席） |
| gamification/points | `PointTransaction` | `pointtransactions` | 點數交易紀錄（正數=獲得、負數=扣除） |
| gamification/points | `ClassPointConfig` | `classpointconfigs` | 班級點數設定（打卡/繳交各幾分） |
| gamification/badges | `BadgeDefinition` | `badgedefinitions` | 徽章定義（名稱、圖示、觸發條件）；`trigger_rule_id` 與 `trigger_key` 互斥 |
| gamification/badges | `BadgeAward` | `badgeawards` | 徽章頒發紀錄 |
| gamification/triggers | `TriggerRule` | `triggerrules` | 觸發規則：class_id, name, expression, is_active, created_by, created_at, updated_at |
| gamification/prizes | `Prize` | `prizes` | 獎品（線上 / 實體） |
| community/feed | `FeedPost` | `feedposts` | 班級動態貼文 |
| community/feed | `Reaction` | `reactions` | 貼文表情回應 |

---

## 6. Extension Registry（擴充註冊中心）

DPRS 使用 **Protocol-based Plugin System（基於 Protocol 的套件系統）** 實現可擴充架構。核心由兩個部分組成：

### 6.1 Protocol 介面

定義於 `src/extensions/protocols/`，每個 Protocol 使用 `@runtime_checkable` 裝飾器，在註冊時進行型別檢查：

| Protocol | 檔案 | 用途 |
|---|---|---|
| `AuthProvider` | `auth.py` | 認證提供者（帳密、OAuth 等） |
| `RewardProvider` | `reward.py` | 獎勵提供者（打卡得分、繳交得分） |
| `BadgeTrigger` | `badge.py` | 徽章觸發條件（自動判定是否頒發） |
| `SubmissionValidator` | `validator.py` | 繳交驗證器（自訂驗證邏輯） |

### 6.2 ExtensionRegistry

`ExtensionRegistry` 是一個 Module-level Singleton（模組層級的單例），以 `(Protocol type, key)` 為索引儲存實作：

```python
# 註冊
registry.register(AuthProvider, "local", LocalAuthProvider())
registry.register(RewardProvider, "checkin", CheckinRewardProvider())
registry.register(RewardProvider, "submission", SubmissionRewardProvider())

# 取得單一實作
provider = registry.get(AuthProvider, "local")

# 取得某 Protocol 下所有實作
all_reward_providers = registry.get_all(RewardProvider)
```

**運作機制：**

1. `register()` 時透過 `isinstance()` 驗證實作是否符合 Protocol 介面，不符合則拋出 `TypeError`。
2. 內部以 `dict[type, dict[str, Any]]` 儲存：外層 key 為 Protocol 類型，內層 key 為字串識別碼。
3. `get_all()` 回傳指定 Protocol 下所有已註冊的實作——用於「所有 RewardProvider 依序執行」的場景。

**擴充範例：** 如需新增 Google OAuth 認證，只需實作 `AuthProvider` Protocol 並註冊：

```python
registry.register(AuthProvider, "google", GoogleOAuthProvider())
```

測試時可使用 `TestRegistry` Context Manager（情境管理器）替換全局 Registry，確保測試隔離。

### 6.3 目前已註冊的擴充

| Protocol | Key | 實作類別 | 說明 |
|---|---|---|---|
| `AuthProvider` | `"local"` | `LocalAuthProvider` | 本地帳號密碼認證 |
| `RewardProvider` | `"checkin"` | `CheckinRewardProvider` | 打卡自動發放點數 |
| `RewardProvider` | `"submission"` | `SubmissionRewardProvider` | 繳交任務自動發放點數 |

---

## 7. 技術堆疊

| 層級 | 技術 | 說明 |
|---|---|---|
| **Web Framework** | FastAPI | 非同步 Python Web 框架 |
| **Template Engine** | FastAPI-WebPage (Jinja2) | SSR 伺服器端模板渲染 |
| **ODM** | Beanie | 非同步 MongoDB ODM，基於 Pydantic |
| **Database** | MongoDB (Motor) | 文件式資料庫，Motor 為非同步驅動 |
| **Cache / Session** | Redis | 工作階段儲存與應用程式狀態快取 |
| **Authentication** | PyJWT + bcrypt | JWT Token 簽發 / 密碼雜湊 |
| **CSRF Protection** | 自訂 CSRFMiddleware | 防止跨站請求偽造 |
| **Rate Limiting** | SlowAPI | 基於 IP 的請求速率限制 |
| **HTTP Client** | HTTPX | 非同步 HTTP Client（外部整合用） |
| **Encryption** | cryptography | 加密工具套件 |
| **DSL Engine** | Rust (pest 2.8, wasm-bindgen 0.2, pyo3 0.25) | DSL 表達式引擎，編譯為 WASM（前端）與 PyO3（後端） |
| **Frontend Editor** | CodeMirror 6 (ESM CDN) | DSL 編輯器，語法高亮 / 自動完成 / hover |
| **Frontend WYSIWYG** | Milkdown (ESM CDN) | 所見即所得 Markdown 編輯器 |
| **Runtime** | Python 3.13+ | 最低要求版本 |
| **Package Manager** | uv | 快速 Python 套件管理工具 |
| **License** | ECL-2.0 | Educational Community License |
