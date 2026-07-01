## Why

目前密碼 hash 使用 passlib + bcrypt。passlib 自 2020 年後停止維護（PyPI 最後版本 1.7.4），已知在 Python 3.13 因 `crypt` module 移除而無法正常運作，且與 bcrypt 4.1+ 存在版本偵測相容問題。argon2-cffi 是目前 Django、PyPI/Warehouse、FastAPI 生態系共同採用的現代密碼 hash 函式庫，由 Python 社群知名維護者（Hynek Schlawack）積極維護，提供 OWASP 推薦的 Argon2id 演算法預設參數。

本專案即將進入 beta 前置階段，目前無真實用戶資料，是一次性切換的最佳時機。同時作為教學平台，展示現代密碼 hash 最佳實踐也有教育意義。

## What Changes

- 移除 `passlib[bcrypt]` 和 `bcrypt` 依賴
- 新增 `argon2-cffi` 依賴
- `src/core/auth/password.py`：以 `argon2.PasswordHasher` 取代 `passlib.context.CryptContext`
- `src/core/auth/local_provider.py`：將 `DUMMY_HASH` 從 bcrypt 格式更新為 argon2 格式，同步更新相關 comments
- `tests/test_auth.py`：更新 `DUMMY_HASH` 格式斷言（`$2b$` → `$argon2id$`）
- 所有透過 `hash_password()` / `verify_password()` 間接使用的程式碼無需修改（抽象層封裝完整）

## Non-Goals

- 不做漸進式遷移（不保留 bcrypt 向後相容），因為目前無真實用戶資料
- 不自訂 argon2 參數，直接使用 argon2-cffi 的 OWASP 推薦預設值
- 不更換 `password.py` 對外的函式介面（`hash_password`、`verify_password`、`validate_password_strength` 維持不變）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `user-auth`：密碼 hash 演算法從 bcrypt 改為 Argon2id，新增演算法選用的明確 requirement

## Impact

- 受影響 spec：`user-auth`（新增密碼 hash 演算法 requirement）
- 受影響程式碼：
  - `src/core/auth/password.py`（核心改動）
  - `src/core/auth/local_provider.py`（dummy hash 更新）
  - `tests/test_auth.py`（格式斷言更新）
  - `pyproject.toml`（依賴替換）
