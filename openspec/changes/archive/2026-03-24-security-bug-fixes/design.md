## Context

安全審計發現 7 項中等嚴重度的安全問題（R7–R13），涵蓋 runtime bug、資訊洩漏、timing side-channel、缺少輸入驗證、權限提升與部署設定問題。

## Goals / Non-Goals

**Goals:**

- 修復 7 項安全問題，不改變現有功能行為與架構

**Non-Goals:**

- 不重構 permission system 架構
- 不新增 rate limiting 或 CSRF token（屬不同安全層級）
- 不改變 API 介面或回傳格式

## Decisions

### R7: prizes router — 改用 IdentityTag 檢查

**決策**：將 `user.role` 改為 `IdentityTag.STUDENT in user.identity_tags` 取代不存在的 `user.role` 屬性。

**理由**：User model 無 `role` 欄位，現有系統使用 IdentityTag 來辨識身分。此為最小修正，與其他端點的身分判斷模式一致。

### R8: 錯誤訊息清理 — 只清理 catch-all exception

**決策**：只清理 `except Exception` 的 catch-all handler（`system/router.py` 等），將 `detail=str(e)` 改為通用錯誤訊息並保留 `logger.exception(e)` 記錄。保留 `except ValueError` 的已知安全訊息不變。

**理由**：ValueError 是業務邏輯主動拋出的錯誤，訊息內容可控且不含敏感資訊。catch-all `Exception` 則可能暴露堆疊、SQL 語句或內部路徑。

### R9: login timing — dummy bcrypt verify

**決策**：在 `src/core/auth/local_provider.py` 的 user-not-found 路徑加入 `verify_password("dummy", DUMMY_HASH)` 以消除 timing difference。

**理由**：bcrypt verify 約 100–300ms，若 username 不存在直接回傳則攻擊者可透過回應時間判斷使用者是否存在。加入 dummy verify 使兩條路徑的時間一致。

### R10: 密碼強度驗證 — 共用函式

**決策**：在 `src/core/auth/password.py` 新增 `validate_password_strength()` 函式（最少 8 字元），套用至所有 user creation / password change 端點。

**理由**：集中驗證邏輯，避免在各端點重複實作。最少 8 字元與現有 setup wizard 的密碼長度要求一致。

### R11: CSV 匯入大小限制 — 檔案大小檢查

**決策**：在 CSV import endpoint 讀取前檢查 Content-Length 或用 chunk 讀取限制，上限 1MB。

**理由**：無限制的檔案上傳可被用於 denial-of-service 攻擊。1MB 對 CSV 匯入而言已綽綽有餘。

### R12: 權限提升防護 — caller 權限上限檢查

**決策**：在 `src/core/users/router.py` 的 create_user、update_user、bulk_update_permissions 中加入 `if new_perms & ~caller_perms: raise 403` 檢查。

**理由**：MANAGE_USERS 權限允許管理使用者，但不應允許設定比自身更高的權限。此為最小權限原則（Principle of Least Privilege）的實作。

### R13: FORWARDED_ALLOW_IPS — 環境變數可配置

**決策**：在 `Dockerfile` 將 `FORWARDED_ALLOW_IPS=*` 改為 `os.getenv("FORWARDED_ALLOW_IPS", "")`，預設為空。

**理由**：`*` 表示信任所有代理的 X-Forwarded-For header，可被用於 IP spoofing。改為環境變數可配置，讓部署者根據實際環境設定。

## Risks / Trade-offs

- [R9 dummy verify 增加 CPU 開銷] → 只在 user-not-found 時執行，頻率低，影響可忽略。
- [R10 密碼強度驗證可能影響既有弱密碼使用者] → 只影響新建/修改密碼操作，不影響既有登入。
- [R12 權限檢查可能影響合法的管理操作] → 只限制設定「高於自身」的權限，正常管理操作不受影響。
