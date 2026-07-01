## 1. 修復 prizes router runtime bug

- [x] 1.1 修復 `src/gamification/prizes/router.py:59` 的 `user.role` 引用，改為 IdentityTag 檢查

## 2. 錯誤訊息清理

- [x] [P] 2.1 修改 `src/core/system/router.py` 的 `except Exception as e` 為通用錯誤訊息，保留 log

## 3. Login timing 修復

- [x] [P] 3.1 在 `src/core/auth/local_provider.py` 的 user-not-found 路徑加入 dummy bcrypt verify

## 4. 密碼強度驗證

- [x] 4.1 在 `src/core/auth/password.py` 新增 `validate_password_strength()` 函式
- [x] 4.2 套用至 `src/core/users/router.py` create user、`src/core/auth/router.py` change password、CSV import

## 5. CSV 匯入大小限制

- [x] [P] 5.1 在 `src/core/users/router.py` CSV import endpoint 加入檔案大小檢查（上限 1MB）

## 6. 權限提升防護

- [x] [P] 6.1 在 `src/core/users/router.py` 的 create_user、update_user、bulk_update_permissions 中驗證 caller 不可設定高於自身的權限

## 7. FORWARDED_ALLOW_IPS 修復

- [x] [P] 7.1 在 `Dockerfile` 將 FORWARDED_ALLOW_IPS 改為環境變數可配置
