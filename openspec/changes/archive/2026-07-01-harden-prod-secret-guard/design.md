## Context

正式部署一律以 `FASTAPI_APP_ENVIRONMENT=prod` 啟動（見 `scripts/docker-entrypoint.sh:12`、`.env.example`、`docker-compose.yml`），但應用程式碼有 4 處各自以 `os.getenv("FASTAPI_APP_ENVIRONMENT", ...) == "production"` 判定環境：

- `src/core/auth/jwt.py` 的 `check_secret_safety()`
- `src/core/auth/router.py:30` 的 `_is_production()`
- `src/pages/router.py:26` 的 `_is_production()`
- `src/shared/sessions.py:119` 的 inline `is_production` 判定（send_wrapper 內）

由於 `"prod" != "production"`，依文件部署的正式環境會被判為非正式環境，**靜默**關閉 Secure cookie 與預設密鑰啟動防護。這是本變更要修掉的承載型 bug。

同時存在兩個次要問題：

1. `check_secret_safety()` 只比對唯一字串 `dev-secret-change-in-production`，擋不住公開於 repo 的 `.env.example` 內 `SESSION_SECRET=changeme_session`，也擋不住任何過短的弱密鑰。
2. `src/main.py:95` 以 `os.getenv("SESSION_SECRET") or secrets.token_hex(32)`（隨機退路）建立 SessionMiddleware 密鑰，而 `src/core/auth/jwt.py:9` 以 `os.getenv("SESSION_SECRET", _DEFAULT_SECRET)`（固定預設字串退路）取得 JWT 密鑰。當 `SESSION_SECRET` 未設定時兩者分歧。

本變更屬於安全相關修改。依專案 `CLAUDE.md` 與 `docs/security-notes.md` 規範，已先行查閱安全備查紀錄（本變更不觸及 Badge IDOR、`| safe` 模板渲染、CSRF/SameSite cookie 設定，與既有 SEC-DESIGN/SEC-WATCH 條目不衝突）。

## Goals / Non-Goals

**Goals:**

- 環境判定收斂為單一事實來源 `is_production()`，並對 `FASTAPI_APP_ENVIRONMENT` 做 `strip()` + 轉小寫正規化，同時接受 `prod` 與 `production`。
- entrypoint 與應用程式對「何謂正式環境」的判定一致。
- `check_secret_safety()` 能擋下預設值、含 `changeme` 的密鑰與過短密鑰；正式環境 raise、其他環境 warn。
- JWT 簽章與 SessionMiddleware 共用同一把實際密鑰，且驗證的就是這把密鑰。
- 開發／未設定環境行為不退步（仍為非正式環境、仍保有便利的隨機退路）。

**Non-Goals:**

- 不變更 cookie 的 `SameSite` 設定，亦不調整 CSRF 策略（避免牽動 `docs/security-notes.md` 的 SEC-DESIGN-001）。
- 不導入 secret manager／KMS 等外部密鑰管理基礎設施。
- 不新增 `staging` 等第三種環境語意；非 `{prod, production}` 一律視為非正式環境。
- 不更動 JWT 演算法、token 結構或有效期。

## Decisions

### is_production() single source of truth

於新檔 `src/shared/environment.py` 提供 `is_production() -> bool`，於**呼叫時**（非 module load 時）讀取環境變數，以利測試以 monkeypatch 覆寫 `os.environ`：

```python
def is_production() -> bool:
    raw = os.getenv("FASTAPI_APP_ENVIRONMENT", "")
    return raw.strip().lower() in {"prod", "production"}
```

並依 `src/shared/__init__.py` 既有 `from .module import name` + `__all__` 慣例匯出 `is_production`（與 `get_session_secret`）。

4 處 inline 判定全部改用此 helper：

- `src/core/auth/router.py` 與 `src/pages/router.py` 的 `_is_production()` 改為 `return is_production()` 的薄委派 —— 既收斂事實來源，又維持既有 `tests/test_secure_cookie.py` 直接呼叫 `auth_router_mod._is_production()` / `pages_router_mod._is_production()` 的相容性（正規化後 `production` 仍為 True、`staging` 仍為 False，舊測試不退步）。
- `src/shared/sessions.py` 的 send_wrapper 與 `src/core/auth/jwt.py` 的 `check_secret_safety()` 直接呼叫 `is_production()`。

**替代方案**：在各模組各自做正規化字串比對。否決，因為這正是 4 處分歧的根因；單一 helper 才能保證一致。

### Weak-secret rejection policy

`check_secret_safety()` 強化為對「實際使用的密鑰」做三項弱密鑰判定：

1. 內含開發預設值 `_DEFAULT_SECRET`（`dev-secret-change-in-production`）。採子字串比對（`_DEFAULT_SECRET in secret`）而非相等比對，使「以預設值補上任意數量字元」的近預設弱密鑰（例如 33 字元的 `dev-secret-change-in-production!!`，已超過長度門檻）也會被擋下，而非僅擋下剛好相等或剛好 32 字元的情形。
2. 不分大小寫含有子字串 `changeme`（涵蓋 `.env.example` 的 `changeme_session`）。
3. 長度不超過 32 字元（含剛好 32 字元；真正的 `secrets.token_hex(32)` 為 64 個十六進位字元，遠超門檻）。判定採 `<=` 而非 `<`，以擋下剛好 32 字元的近預設弱密鑰。

命中任一條件即視為不安全：`is_production()` 為 True 時 `raise RuntimeError`，訊息需可行動（指出產生方式 `python -c "import secrets; print(secrets.token_hex(32))"` 並要求設定 `SESSION_SECRET`）；否則 `_logger.warning(...)`。函式保持可被 import 與單獨呼叫測試，簽章採 `check_secret_safety(secret: str | None = None)`：`secret` 省略時解析為實際使用密鑰，傳入時驗證該字串，方便測試。logger 名稱維持 `core.auth.jwt` 以相容既有 caplog 測試。

**替代方案**：以最小長度或熵值演算法（zxcvbn）評估強度。否決，過重且引入相依；「預設值／`changeme`／<32」三條件已能擋下所有已知的可預測密鑰，且易於測試與說明。

### SESSION_SECRET resolver unification

於 `src/shared/environment.py` 提供單一 resolver，讓 JWT 與 SessionMiddleware 共用同一把密鑰：

```python
_DEFAULT_SECRET = "dev-secret-change-in-production"
_FALLBACK_SECRET = secrets.token_hex(32)  # 每個 process 僅產生一次

def get_session_secret() -> str:
    env = os.getenv("SESSION_SECRET")
    return env if env else _FALLBACK_SECRET
```

關鍵設計：

- **呼叫時讀 env、僅快取隨機退路**。`SESSION_SECRET` 於呼叫時讀取（測試可 monkeypatch）；未設定時回傳 process 層級**只產生一次**的 `_FALLBACK_SECRET`，確保同一 process 內 JWT 與 SessionMiddleware 拿到的退路密鑰相同（解掉 main.py 與 jwt.py 的分歧），而非每次呼叫各自隨機。
- `src/main.py` 改以 `get_session_secret()` 建立 SessionMiddleware 密鑰，取代 `os.getenv("SESSION_SECRET") or secrets.token_hex(32)`。
- `src/core/auth/jwt.py` 的 `create_access_token` / `decode_access_token` 與 `check_secret_safety()` 皆改用 `get_session_secret()` 解析，使「驗證的密鑰」即「簽章用的密鑰」。
- 開發未設定時退路為 64-hex 隨機值（安全且便利）；正式環境則由 `check_secret_safety()` 把關 —— 操作者若使用 `changeme_session`／預設值／過短值會被擋下，明確要求設定強密鑰。

**替代方案 A**：module load 時一次性快取整把密鑰（含 env）。否決，會使測試 monkeypatch `SESSION_SECRET` 失效。
**替代方案 B**：未設定時於正式環境直接 raise。本變更採較保守路線：保留隨機退路、由弱密鑰政策把關可預測密鑰；是否將「正式環境未設定」升級為硬性 raise 列為 Open Question。

### docker-entrypoint.sh environment parity

`scripts/docker-entrypoint.sh` 的 production 分支由 `[ "$FASTAPI_APP_ENVIRONMENT" = "prod" ]` 擴充為同時接受 `prod` 與 `production`：

```sh
if [ "$FASTAPI_APP_ENVIRONMENT" = "prod" ] || [ "$FASTAPI_APP_ENVIRONMENT" = "production" ]; then
```

使「啟動哪一種 server」與「應用程式是否視為正式環境」由同一組關鍵字決定，杜絕 entrypoint 與 app 判定分歧。

## Implementation Contract

- **Behavior — 環境判定**：`is_production()` 在 `FASTAPI_APP_ENVIRONMENT` 經去頭尾空白並轉小寫後屬於 `{"prod", "production"}` 時回傳 `True`；`dev`、`development`、未設定、`staging` 等其餘值回傳 `False`。於呼叫時讀取環境變數。
- **Behavior — Secure cookie**：登入端點（`POST /auth/login` 與 `POST /pages/login`）在 `is_production()` 為 True 時，於 `access_token` cookie 帶 `Secure` 旗標；為 False 時不帶。`prod` 與 `production` 皆視為正式環境。
- **Behavior — 啟動密鑰防護**：`check_secret_safety()` 在實際使用密鑰命中弱密鑰政策（等於 `_DEFAULT_SECRET`／含 `changeme`／長度 ≤ 32）時，正式環境 `raise RuntimeError`（訊息含設定指引），非正式環境記錄 WARNING；強密鑰（如 64-hex）在正式環境不 raise 亦不 warn。
- **Interface**：
  - `src/shared/environment.py`：`is_production() -> bool`、`get_session_secret() -> str`、模組常數 `_DEFAULT_SECRET`。
  - `src/shared/__init__.py`：依既有慣例於 `__all__` 匯出 `is_production`、`get_session_secret`。
  - `core.auth.jwt.check_secret_safety(secret: str | None = None) -> None` 維持可 import；logger 名稱為 `core.auth.jwt`。
- **Failure mode**：正式環境弱密鑰 → `RuntimeError`，於 `src/main.py` lifespan 啟動時拋出，阻止啟動。非正式環境 → WARNING log，不阻擋。
- **Acceptance criteria**：以 `.venv/bin/python -m pytest`（非 `uv run`）執行，涵蓋 `is_production()` 真值表、`check_secret_safety()` 三條件在正式環境 raise／開發 warn／強密鑰 pass，以及登入 Secure 旗標在正式／非正式環境的有無。`spectra validate harden-prod-secret-guard` 通過。
- **Scope boundaries**：僅調整環境判定、弱密鑰政策、密鑰 resolver 與 entrypoint 字串比對。不動 SameSite／CSRF／JWT 演算法／token 結構，不新增外部相依。

## Risks / Trade-offs

- [既有測試 `tests/test_secure_cookie.py` 直接呼叫各 router 的 `_is_production()`] → 保留 `_is_production()` 為薄委派而非刪除，正規化後既有斷言（`production` → True、`staging` → False）仍成立。
- [既有 `tests/test_security_audit.py` 以 `jwt_module._SECRET` 直接覆寫驗證 warning] → `check_secret_safety()` 改以 resolver 解析並接受 `secret` 參數，apply 階段需同步更新該測試的設定方式；行為（預設值在非正式環境 warn）維持一致。
- [開發未設定 `SESSION_SECRET` 時退路為隨機值，跨 process／worker 不一致] → 屬開發便利取捨；正式部署一律要求顯式設定 `SESSION_SECRET`，並由弱密鑰政策把關。
- [將 `changeme` 列為不分大小寫的禁用子字串] → 合法但剛好含該子字串的密鑰會被誤判；機率極低且訊息會明確指引，可接受。

## Migration Plan

1. 新增 `src/shared/environment.py` 與 `__init__.py` 匯出，4 處 inline 判定改為委派／呼叫 helper。
2. 強化 `check_secret_safety()` 與統一 resolver，更新 `src/main.py`。
3. 更新 `scripts/docker-entrypoint.sh`。
4. 補上／更新測試，以 `.venv/bin/python -m pytest` 全綠後再交付。
5. 回滾策略：本變更為純程式碼層級，無資料移轉；如需回滾直接還原上述檔案即可。正式部署者應確認已將 `SESSION_SECRET` 設為強隨機值，否則新防護會在啟動時擋下。

## Open Questions

- 正式環境若 `SESSION_SECRET` 完全未設定（退路為隨機 64-hex），是否應由 warn／pass 升級為硬性 `raise`？本變更暫採保守路線（隨機退路視為足夠強），留待後續決定。
