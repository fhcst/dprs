## Why

未登入存取受保護頁時，`src/pages/deps.py` 的 `_redirect_to_login` 以 `str(request.url)`（**絕對 URL**）組 `next`；但登入 POST 在 `src/pages/router.py` 的驗證只接受**相對路徑**（`next.startswith("/") and not next.startswith("//")`）。絕對 URL 永遠通不過驗證 → `safe_next=None` → 登入後一律 fallback 到 dashboard，**deep-link 返回（登入後回到原本要去的頁）形同失效**。

同時，現行字串前綴驗證仍會放行 `/\evil.com`（以單一 `/` 開頭、非 `//`）：瀏覽器會把 `\` 正規化成 `/` → 變成 protocol-relative 跳轉至外站。此為**真實存在但低嚴重度的 open-redirect 旁路**，須與 deep-link 修復一併關閉。

## What Changes

本案為 **Bug Fix ＋ 安全硬化**（來源 finding BUG-4，含對抗式審查補充的 `/\` 邊角），影響 `src/pages/deps.py` 與 `src/pages/router.py` 兩檔。

- **修復 deep-link 返回**：`_redirect_to_login` 改存**相對路徑**——`request.url.path`，並在原請求帶 query string 時一併保留（`path + "?" + query`），讓存入的 `next` 與登入端驗證器的相對路徑格式一致，登入後可正確回到原請求頁。
- **硬化 `next` 開放轉址驗證**：登入 POST 的 `next` 驗證收緊為「只接受單一 `/` 開頭的同源相對路徑」。**先拒絕／正規化反斜線**——任何含 `\`、`//`、`:` 或控制字元的 `next` 一律拒絕；不可單獨倚賴 `urlsplit(next).netloc == ""`（`/\evil.com` 的 netloc 為空、path 仍含 `\`，會被旁路）。此修法須關閉 `/\evil.com` 旁路。
- **新增迴歸測試**：於 `tests/test_pages.py` 補測——合法相對 `next` 來回返回原頁；以及 `//evil`、`/\evil`、`http://evil`、`https://evil` 全部被拒並 fallback 至 dashboard，外加一個合法相對路徑被允許。
- **不更動 cookie SameSite 或任何 CSRF 設定**（依安全守則，登入 cookie `samesite="lax"` 與 CSRF 策略維持不變）。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `user-auth`：修改「Browser-based form login endpoint」requirement（明訂登入成功後依已驗證的安全相對路徑決定轉址目標、否則 fallback dashboard，並界定開放轉址驗證規則——先拒絕反斜線等向量、不可單靠 netloc 空值判斷），並新增「Login redirect preserves the requested page as a relative next」requirement（規範 require-login 轉址時以相對路徑——path ＋ 必要時 query——保存目標，保證與登入端驗證器格式一致、可來回返回）。

## Impact

- 受影響程式碼：
  - `src/pages/deps.py`（`_redirect_to_login`：`str(request.url)` → 相對 `request.url.path`＋query）
  - `src/pages/router.py`（`login_form` 的 `next` 驗證：硬化為先拒反斜線／`//`／`:`／控制字元的同源相對路徑檢查）
- 受影響測試：`tests/test_pages.py`（新增 deep-link 返回與 open-redirect 向量迴歸測試）
- 受影響 specs：`user-auth`（form login 轉址行為 ＋ 相對 `next` 保存契約）
- 不動 cookie SameSite、不動 CSRF 設定、無 API／資料模型／相依套件變更。
