## Context

登入流程橫跨兩個檔案、且其中一段是安全敏感的開放轉址（open-redirect）防護，故以 design.md 釐清技術取捨。

現況（已逐行查核）：

- `src/pages/deps.py` 的 `_redirect_to_login`：以 `request.url_for("login_page").include_query_params(next=str(request.url))` 組登入轉址。`str(request.url)` 是**絕對 URL**（含 scheme/host）。
- `src/pages/router.py` 的 `login_form`：`if next and next.startswith("/") and not next.startswith("//"): safe_next = next`，登入成功後 `redirect_url = safe_next or str(request.url_for("dashboard_page"))`。

兩者格式不一致：deps 存「絕對 URL」、router 只收「相對路徑」→ `next` 永遠驗不過 → 一律 fallback dashboard，deep-link 返回死掉。

安全前提：現行前綴檢查雖擋掉 `//evil`、`http(s)://evil`，但**仍放行 `/\evil.com`**（以單一 `/` 開頭、非 `//`）。部分瀏覽器把 `Location` 內的 `\` 正規化成 `/` → 形成 protocol-relative 跳轉至外站。屬低嚴重度但真實存在的旁路。專案安全守則要求「JSON API 依賴 CORS preflight + SameSite cookie 防護，不要變更 cookie SameSite」，故本案**不得**動 SameSite 或 CSRF。

## Goals / Non-Goals

**Goals:**

- 讓登入後能正確回到原請求頁（deep-link 返回可用）。
- 關閉 `/\evil.com` 開放轉址旁路；`//evil`、`http://evil`、`https://evil` 維持被擋。
- 以最小、檔案侷限的改動完成，僅動 `src/pages/deps.py`、`src/pages/router.py`、`tests/test_pages.py`。

**Non-Goals:**

- 不更動 cookie `samesite="lax"` 設定、不更動任何 CSRF 策略。
- 不引入第三方 URL 驗證套件；以標準庫 `urllib.parse.urlsplit` ＋ 字元檢查即可。
- 不改 `next` 以外的登入流程（rate limit、PRG error 轉址、secure cookie 等維持不變）。
- 不處理 handoff §4 提到的其他自製 redirect 稽核（非本案 scope，另案評估）。

## Decisions

### deps.py 改存相對路徑 next

`_redirect_to_login` 改為以**相對路徑**作為 `next`：取 `request.url.path`，當 `request.url.query` 非空時組成 `path + "?" + query`，再 `include_query_params(next=<relative>)`。

理由：登入端驗證器只認相對路徑；deps 端存相對路徑才能讓 `next` 通過驗證並來回返回。`request.url.path` 在 Starlette 為純路徑（不含 host、不含 query），與「單一 `/` 開頭同源相對路徑」格式天然吻合。保留 query 是因為部分受保護頁靠 query 還原狀態（例如 `?create_class=1`）。

替代方案：保留絕對 URL、改在登入端把絕對 URL 拆出 path——被否決，因為這把「信任外部輸入再拆解」的負擔留在安全敏感點，且 deps 端本就知道自己的相對路徑，於來源端存相對值最單純、攻擊面最小。

### router.py 硬化 next 驗證器

把 `next.startswith("/") and not next.startswith("//")` 換成「先拒絕危險字元、再確認同源相對路徑」的兩段式驗證：

1. **先拒絕／正規化反斜線等向量（只檢查 path/authority 段）**：取 `next` 第一個 `?` 或 `#` 之前的 path 段，若該段含 `\`、以 `//` 開頭、或含 `:`，直接視為不安全；另外若整串含任何 ASCII 控制字元（`ord < 0x20`）亦視為不安全。**authority 檢查刻意略過 query/fragment**：query 內的 `:`（ISO 時間戳、`?from=10:30`、比值）只是停在本站的同源資料，不構成跨站向量，必須能來回返回而非被靜默丟棄。
2. 再要求 `next` 以單一 `/` 開頭，且（採 `urlsplit` 後）`scheme` 與 `netloc` 皆為空。

關鍵理由（對抗式審查實證）：**`urlsplit(next).netloc == "" 單獨用不夠**——`urlsplit("/\evil.com")` 的 `netloc` 為空、但 `path` 仍含 `\`，瀏覽器會把 `\` 正規化成 `/` 造成 protocol-relative 跳轉。因此**必須先排除 path 段的反斜線**，netloc/scheme 空值檢查只能作為輔助、不可單獨替代。把 `\`／`//`／`:` 的判斷收斂到 path 段，既擋掉 `/\evil.com`、`//evil.com`、`http(s)://evil.com`（其 `:` 落在 path 段），又讓帶 `:` 的合法 query（deep-link 狀態）得以原樣返回。任一驗證失敗即 `safe_next=None`，登入成功後 fallback `GET /pages/dashboard`。

替代方案：純 `urlsplit` 後只看 `netloc`/`scheme`——被否決（會放行 `/\evil.com`）。純字串前綴檢查（現況）——被否決（同樣放行 `/\evil.com`）。故採「反斜線等先拒 ＋ scheme/netloc 皆空」的複合判準。

### 新增 deep-link 返回與 open-redirect 迴歸測試

於 `tests/test_pages.py` 沿用既有 `db_app` fixture 與 `POST /pages/login` 表單流程，補三類斷言：(a) 合法相對 `next`（如 `/pages/settings`）登入後 `Location` 精準等於該相對路徑；(b) `//evil`、`/\evil`、`http://evil`、`https://evil` 四向量登入後 `Location` 皆指向 `/pages/dashboard` 且不含 `evil`；(c) deps 端未登入存取受保護頁時 `next` 為相對路徑（非絕對 URL）。

理由：BUG-4 與其安全邊角必須有可重跑的回歸保護，避免日後再退化。現有 `test_form_login_redirects_to_next_param`、`test_form_login_ignores_unsafe_next_param` 已涵蓋部分情境，本案補齊 `/\evil`、`http://evil`、deep-link 來回與相對 `next` 保存等缺口。

## Implementation Contract

**Behavior**：

- 未登入存取受保護頁時，瀏覽器被 302 導到 `/pages/login?next=<relative>`，其中 `<relative>` 為原請求的相對路徑（例如 `/pages/settings`；若原請求含 query 則為 `/pages/dashboard?create_class=1`），**不再是 `http(s)://…` 絕對 URL**。
- 登入成功且 `next` 為合法同源相對路徑時，302 `Location` 精準等於該相對路徑（deep-link 返回成功）。
- 登入成功但 `next` 缺漏／為空／命中任一 open-redirect 向量（`//evil`、`/\evil`、`http://evil`、`https://evil`）時，302 `Location` 指向 `/pages/dashboard`，且不含外站網域。

**Interface / data shape**：

- `_redirect_to_login(request)` 對外行為不變（仍 raise 302 至 login），唯 `next` query 值由絕對 URL 改為相對路徑字串。
- `login_form` 簽章不變；`next` 驗證邏輯由「字串前綴檢查」改為「先對 path 段（第一個 `?`／`#` 之前）拒反斜線／`//`／`:`、整串拒控制字元，再要求單一 `/` 開頭且 `urlsplit` 後 scheme/netloc 皆空」。`safe_next` 對外語意不變（安全則為該相對路徑、否則 `None`）；含 `:` 的合法 query（如 `?ts=2026-06-28T12:00:00`）視為安全並原樣返回。

**Failure modes**：

- 任何不安全 `next`（含 `/\evil.com` 旁路）→ `safe_next=None` → 靜默 fallback `/pages/dashboard`（不報錯、不外洩 `next` 至 `Location`）。
- 驗證以「先拒絕」為主，不對未知輸入做寬鬆放行（fail-closed）。

**Acceptance criteria**：

- `tests/test_pages.py` 既有測試全綠，且新增測試涵蓋：合法相對 `next` 來回返回原頁；`//evil`、`/\evil`、`http://evil`、`https://evil` 全部 fallback dashboard 且 `Location` 不含 `evil`；deps 端 `next` 為相對路徑。
- 以 `uv run pytest tests/test_pages.py -q` 執行通過。
- 人工以 `git --no-pager diff` 確認僅 `src/pages/deps.py`、`src/pages/router.py`、`tests/test_pages.py` 變更，且 cookie `samesite`／CSRF 相關程式碼未被改動。

**Scope boundaries**：

- 僅改 `src/pages/deps.py` 的 `next` 來源、`src/pages/router.py` 的 `next` 驗證、`tests/test_pages.py` 的測試。
- 不動 cookie SameSite、不動 CSRF、不動 rate limit／secure cookie／PRG error 轉址等其他登入行為。

## Risks / Trade-offs

- [保留 query string 可能把敏感 query 帶進 `next`] → `next` 僅為同源相對路徑、最終只用於本站 302；不外送第三方，風險可忽略；且驗證器仍會擋掉 path 段任何含 `:`／`\`／`//` 的異常值。
- [authority 檢查只看 path 段，是否放鬆了安全？] → 否。可造成跨站跳轉的向量（`//evil`、`/\evil`、`http(s)://evil`）其危險字元一律落在 path/authority 段，仍被擋下；query 段的 `:`／`\` 只是停在本站的資料，瀏覽器不會據此跳轉外站。把檢查收斂到 path 段，純粹是修正「含 `:` 的合法 query（ISO 時間戳、時間/比值）被靜默丟回 dashboard」這個 deep-link 退化，安全邊界不變、仍為 fail-closed。
- [反斜線「先拒」可能誤擋合法但含 `\` 的 path] → 同源 URL path 不應出現裸 `\`（合法路徑會被 percent-encoded 成 `%5C`），fail-closed 對使用者影響趨近於零，安全效益明確。
- [驗證複雜度上升] → 以標準庫 `urlsplit` ＋ 少量字元檢查實作，搭配迴歸測試鎖定四向量與來回返回，維護成本可控。
