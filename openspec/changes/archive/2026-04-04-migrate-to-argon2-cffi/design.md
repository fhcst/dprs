## Context

目前密碼 hash 集中在 `src/core/auth/password.py`，使用 `passlib.context.CryptContext(schemes=["bcrypt"])`。所有 router 和測試透過 `hash_password()` / `verify_password()` 存取，抽象層封裝完整。`local_provider.py` 有一個 hardcoded bcrypt 格式的 `DUMMY_HASH`，用於防止 timing side-channel（CWE-208）。

passlib 自 2020 年停止維護，Python 3.13 已移除其依賴的 `crypt` module，且 bcrypt 4.1+ 存在版本偵測相容問題。

## Goals / Non-Goals

**Goals:**

- 以 argon2-cffi 的 `PasswordHasher` 完全取代 passlib + bcrypt
- 維持 `hash_password()` / `verify_password()` / `validate_password_strength()` 對外介面不變
- 更新 `DUMMY_HASH` 為 argon2 格式，確保 timing side-channel 防護持續有效
- 使用 argon2-cffi 的 OWASP 推薦預設參數

**Non-Goals:**

- 不做 bcrypt → argon2 的漸進式遷移機制（無真實用戶資料）
- 不自訂 argon2 參數（預設值已符合 OWASP 建議）
- 不引入 pwdlib 或 libpass（直接用 argon2-cffi 更透明、教育價值更高）

## Decisions

### 直接使用 argon2-cffi 而非 passlib wrapper

以 `argon2.PasswordHasher` 直接操作，而非透過 passlib 的 CryptContext argon2 scheme。

**理由**：passlib 已停止維護，繼續依賴它只是推遲問題。argon2-cffi 的 `PasswordHasher` 提供等效的高階 API（`hash()`、`verify()`、`check_needs_rehash()`），且由活躍維護者負責。直接使用也讓學生能清楚看到 argon2 的實際運作。

**替代方案**：使用 pwdlib（FastAPI 官方推薦的 passlib 替代品）。不採用，因為 pwdlib 底層也是 argon2-cffi，多一層間接無額外好處。

### verify_password 異常處理策略

argon2-cffi 的 `verify()` 在密碼不符時拋出 `VerifyMismatchError`，而非回傳 `False`。`verify_password()` 需要捕捉此異常並回傳 `bool`，維持現有介面。

**理由**：所有呼叫點（6 個 router 方法 + `local_provider.py`）都期望 `bool` 回傳值，改變介面會造成大量改動。

### DUMMY_HASH 更新方式

在模組層級（module-level）預先計算一個 argon2 格式的 dummy hash，取代現有 bcrypt `$2b$12$...` hash。

**理由**：timing side-channel 防護要求 dummy verify 與真實 verify 耗時一致。若 DUMMY_HASH 保留 bcrypt 格式但驗證引擎換成 argon2，兩者耗時會不同，防護失效。

## Risks / Trade-offs

- **[Risk] argon2 hash 耗時與 bcrypt 不同** → argon2-cffi 預設參數目標 ~40-50ms，bcrypt 約 100-300ms。整體登入 latency 可能下降，但不影響功能。如果未來需要調整，`PasswordHasher` 的參數可以直接修改。
- **[Risk] 測試執行速度變化** → 大量測試使用 `hash_password()` 建立 fixture。argon2 預設耗時較 bcrypt 低，測試可能加速。無需額外處理。
- **[Risk] uv.lock 衝突** → 移除 passlib/bcrypt 並新增 argon2-cffi 會更動 lock file。正常操作，`uv lock` 處理即可。
