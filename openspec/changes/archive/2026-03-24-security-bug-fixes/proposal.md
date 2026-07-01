## Problem

Security audit 發現 7 項中等嚴重度的安全問題：

1. `src/gamification/prizes/router.py:59` 引用不存在的 `user.role` 屬性（runtime error）
2. 12 處 `detail=str(e)` 洩漏內部錯誤訊息（CWE-209）
3. Login 端點因 timing side-channel 可列舉使用者名稱（CWE-208）
4. 無密碼強度驗證（CWE-521）
5. CSV 匯入無檔案大小限制（CWE-400）
6. MANAGE_USERS 管理員可自行提升至 WRITE_SYSTEM（CWE-269）
7. Dockerfile FORWARDED_ALLOW_IPS=* 信任所有代理（CWE-16）

## Root Cause

個別實作疏忽：prizes router 錯誤引用模型欄位、exception handler 直接暴露內部訊息、login handler 對不存在使用者不執行 bcrypt 運算、缺少輸入驗證邏輯。

## Proposed Solution

- R7: 將 `user.role` 改為 IdentityTag 或 permission 檢查
- R8: 將 `except Exception as e: detail=str(e)` 改為通用錯誤訊息（保留 ValueError 的已知安全訊息）
- R9: 在 username 不存在時執行 dummy bcrypt verify
- R10: 建立共用密碼驗證函式（最少 8 字元），套用到所有 user creation/password change 端點
- R11: 在 CSV 匯入前檢查檔案大小上限（如 1MB）
- R12: 在 update user/bulk update 端點驗證 caller 不可設定高於自身的權限
- R13: 將 FORWARDED_ALLOW_IPS 改為環境變數可配置，預設為空

## Success Criteria

- prizes 端點不再 crash
- 錯誤回應不洩漏內部資訊
- login 對存在/不存在使用者的回應時間一致（±10ms）
- 弱密碼被拒絕
- 大於 1MB 的 CSV 被拒絕
- MANAGE_USERS 管理員無法設定 WRITE_SYSTEM 給自己

## Impact

- 受影響的程式碼：
  - `src/gamification/prizes/router.py`
  - `src/tasks/templates/router.py`、`src/tasks/submissions/router.py`、`src/tasks/checkin/router.py`、`src/core/classes/router.py`、`src/core/system/router.py`
  - `src/core/auth/local_provider.py`
  - `src/core/auth/password.py`
  - `src/core/users/router.py`
  - `Dockerfile`
