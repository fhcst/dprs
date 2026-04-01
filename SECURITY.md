# 安全政策 Security Policy

## 支援版本

| 版本    | 支援狀態           |
| ------- | ------------------ |
| 0.5.0   | :white_check_mark: 安全更新支援中 |
| < 0.5.0 | :x: 已停止支援     |

建議所有使用者升級至最新版本以獲得完整的安全修補。

---

## 漏洞通報流程 Vulnerability Reporting

若您發現本專案（每日練習回報系統 / Daily Practice Report System, DPRS）存在安全漏洞，**請勿透過公開的 GitHub Issue 通報**。公開揭露未修補的漏洞可能使現有部署暴露於風險之中。

### 通報方式

請將漏洞詳情以電子郵件寄送至：

> **security@example.com**

郵件中請盡可能包含以下資訊：

- 漏洞類型與嚴重程度評估
- 受影響的元件或端點（endpoint）
- 重現步驟（含環境資訊）
- 概念驗證（Proof of Concept, PoC）程式碼或截圖（如有）
- 您建議的修補方向（如有）

### 回應時程

| 階段             | 預期時程     |
| ---------------- | ------------ |
| 確認收到通報     | 48 小時內    |
| 初步評估與分級   | 5 個工作天內 |
| 修補或緩解方案   | 依嚴重程度而定，重大漏洞優先處理 |
| 通知通報者修補結果 | 修補發布後 3 個工作天內 |

由於本專案為學校教育用途，實際回應時程可能因學期行事曆而有所調整，敬請見諒。

---

## 負責任揭露 Responsible Disclosure

我們遵循負責任揭露（Responsible Disclosure）原則，並感謝所有協助提升本系統安全性的研究者。

### 對通報者的期望

1. **私下通報**：透過上述電子郵件管道通報，不在公開場合揭露漏洞細節。
2. **給予修補時間**：在我們確認並修補漏洞之前，請勿公開漏洞資訊。一般而言，請給予至少 90 天的修補緩衝期。
3. **善意測試**：測試過程中請勿破壞資料、中斷服務，或存取非必要的他人資料。
4. **範圍限制**：請僅針對您自己控制的測試環境進行驗證，不要對正式環境（production）進行攻擊性測試。

### 我們的承諾

- 不會對善意通報的安全研究者採取法律行動。
- 在漏洞修補後，若通報者同意，我們將在更新日誌中致謝。
- 對於所有通報內容，我們將嚴格保密處理。

---

## 已實施的安全措施 Security Measures

以下為本系統目前已實施的安全防護機制：

### 認證與授權 Authentication & Authorization

- **JWT Secret（JSON Web Token 密鑰）啟動驗證**
  正式環境啟動時，若偵測到使用預設密鑰，系統將直接拋出 `RuntimeError` 中斷啟動，防止以弱密鑰運行於正式環境。

- **Cookie Secure 旗標**
  正式環境中，認證 Cookie 強制啟用 `Secure` 旗標，確保 Cookie 僅透過 HTTPS 傳輸。

- **密碼強度驗證（Password Strength Validation）**
  使用者密碼須至少 8 個字元，於建立帳號與變更密碼時皆會驗證。

- **常數時間密碼比對（Constant-Time Comparison）**
  密碼驗證採用常數時間比對演算法，防止計時攻擊（Timing Attack）透過回應時間差異推測密碼內容。

- **權限天花板檢查（Privilege Ceiling Check）**
  建立或修改使用者時，系統檢查操作者不得授予高於自身的權限等級，防止權限提升（Privilege Escalation）。

- **班級範圍授權（Class-Scoped Authorization）**
  所有涉及班級資料的操作皆實施班級範圍授權檢查，防止跨班級存取（Cross-Class Access），對應 CWE-639（授權繞過）與 CWE-863（不正確授權）。

### 速率限制與請求防護 Rate Limiting & Request Protection

- **速率限制（Rate Limiting）**
  認證相關端點透過 slowapi 實施速率限制，減緩暴力破解（Brute Force）與撞庫攻擊（Credential Stuffing）的風險。

- **CSRF 防護（跨站請求偽造防護，Cross-Site Request Forgery Protection）**
  表單 POST 請求透過 `Origin` / `Referer` 標頭驗證，防止跨站請求偽造攻擊。

### 基礎設施安全 Infrastructure Security

- **Docker 基礎設施認證**
  MongoDB 與 Redis 服務皆設定帳號密碼認證，不允許匿名存取。

- **資料庫埠綁定 127.0.0.1**
  資料庫服務僅綁定於 `127.0.0.1`（本機迴路位址），不對外部網路開放埠號，降低未授權存取風險。

- **mongo-express 預設停用**
  mongo-express 管理介面置於 Docker Profile 之下，預設不啟動，僅在開發需要時手動啟用，避免管理介面暴露於正式環境。

### DSL 沙箱安全模型

- **純求值引擎**
  DSL 引擎為純求值引擎，不執行任何 I/O、資料庫查詢或網路呼叫。

- **白名單制**
  僅允許 7 個內建變數（`checkin_count`、`checkin_streak`、`submission_count`、`points`、`badge_count`、`event.type`、`event.occurred_at`）和 3 個內建函數（`count`、`day_of_week`）。

- **表達式安全限制**
  無賦值語句、無迴圈、無任意函數呼叫 — 表達式不可能無限執行。

- **Class-scoped 資料隔離**
  EvalContext 由 service 層從 CBAC 過濾後的資料組裝，DSL 引擎無法存取跨班級資料。

- **執行環境隔離**
  後端使用 PyO3 native binding 執行，前端使用 WASM 在瀏覽器沙箱中執行。

### ClassMembership 唯一性保障

- **唯一複合索引**
  `(class_id, user_id)` unique compound index 防止資料庫層面的重複成員。

- **原子操作保障**
  `ensure_membership()` 使用 MongoDB atomic `update_one` + `upsert=True` + `$setOnInsert`，在並發請求下仍保持正確。

- **所有建立路徑皆處理重複**
  所有 4 個 membership 建立路徑（class 建立、邀請碼加入、公開加入、批次邀請）均處理 `DuplicateKeyError`。

### Rich Text Editor 安全

- **Milkdown 安全 DOM 操作**
  Milkdown 基於 ProseMirror，使用 sanitized DOM 操作而非 innerHTML。

- **CodeMirror 6 純文字處理**
  CodeMirror 6 為純文字編輯器，不解釋或執行使用者輸入。

- **WASM 瀏覽器沙箱隔離**
  WASM 模組在瀏覽器沙箱中執行，無法存取 DOM、cookie 或 localStorage（除透過明確的 JS bridge）。

---

## 聯絡資訊

若有任何安全相關疑問，請聯繫：**security@example.com**
