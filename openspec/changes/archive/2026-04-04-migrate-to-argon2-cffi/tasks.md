## 1. 依賴替換

- [x] 1.1 更新 `pyproject.toml`：移除 `passlib[bcrypt]` 和 `bcrypt>=4.0.0,<5.0.0`，新增 `argon2-cffi`
- [x] 1.2 執行 `uv lock` 更新 lock file

## 2. 核心實作 — Password hashing uses Argon2id

- [x] 2.1 直接使用 argon2-cffi 而非 passlib wrapper：重寫 `src/core/auth/password.py`，以 `argon2.PasswordHasher` 取代 `passlib.context.CryptContext`，並實作 verify_password 異常處理策略（捕捉 `VerifyMismatchError` 回傳 `bool`，維持現有介面）
- [x] 2.2 DUMMY_HASH 更新方式：在 `src/core/auth/local_provider.py` 以 `argon2.PasswordHasher` 預先計算 argon2 格式的 dummy hash 取代 bcrypt `$2b$12$...` hash，更新所有相關 comments 以反映 Argon2id timing-safe dummy verification for unknown users

## 3. 測試更新與驗證

- [x] 3.1 更新 `tests/test_auth.py` 中 `DUMMY_HASH` 格式斷言：將 `startswith("$2")` 改為 `startswith("$argon2id$")`，更新相關 docstring 描述
- [x] 3.2 執行完整測試套件（`pytest`），確認所有測試通過，驗證 password hashing uses Argon2id 行為正確
