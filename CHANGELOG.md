# Changelog

本檔案記錄本專案所有重要變更。格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [1.0.0] - 2026-07-01

### Added（新增）

- **Achievement DSL Engine**（Rust，編譯為 WASM 供前端使用 + PyO3 供後端使用）— 教師可使用表達式語言定義徽章觸發條件（例如 `checkin_streak >= 7 AND submission_count >= 3`）；整合 CodeMirror 6 編輯器，提供即時驗證、自動補全、hover 提示；支援前端 dry-run 測試
- **徽章管理 v2** — Badge Detail Modal（可查看已頒發/未頒發學生名單）、Soft Delete 撤銷機制並附帶稽核紀錄（audit trail）
- 徽章管理側邊欄導覽連結
- DSL Help Modal — 提供完整語法參考說明
- **邀請碼加入審查流程** — 教師須核准加入申請；系統優先列舉已知學生
- **Discord 訊息模板自訂** — 教師可自訂 Webhook 通知格式
- **Docker Buildx 跨平台建置腳本**（`scripts/docker-build.sh`）— 支援 `linux/amd64` + `linux/arm64`
- **容器啟動自動資料庫遷移**（`docker-entrypoint.sh`）
- 觸發規則管理 API（`src/gamification/triggers/`）
- **獎品兌換（Prize Redemption）** — 學生以點數兌換獎品，串起點數經濟的最後一哩
- **Cloudflare Tunnel 部署** — 以 `cloudflared` 作為唯一對外入口（profile `tunnel`），token/protocol 走 `.env`
- **GHCR 預建映像** — `docker compose up` 預設 pull `ghcr.io/fhcst/dprs`，本機 build 移入 opt-in profile；GitHub Actions 於 version tag 自動發佈 multi-arch 映像
- **MongoDB 備份** — `scripts/backup.sh` 與選配 `mongo-backup` 排程 service（profile `backup`）

### Security（安全性）

- **IDOR 修補**：徽章手動頒發端點現已驗證學生班級成員資格
- **計時旁路漏洞（CWE-208）**：對未知使用者名稱執行假 bcrypt 驗證，防止帳號枚舉攻擊
- **CSRF 防護**：新增 `src/shared/csrf.py`
- **速率限制**：新增 `src/shared/limiter.py`
- **JWT 啟動強制檢查**：生產環境若 `SESSION_SECRET` 為預設值則拋出 `RuntimeError` 拒絕啟動
- 生產環境強制 Secure Cookie 旗標
- 學生提交頁面：非成員回傳 HTTP 403
- **修正 `FASTAPI_APP_ENVIRONMENT` 不一致**導致正式環境靜默關閉 Secure cookie 與弱密鑰守門
- **跨班授權全面收斂（release 前 security audit）**：教師提交列表/審閱頁、出缺勤頁、範本清單/新增/編輯/指派頁、點數管理頁一律強制 class-scoped 授權（CWE-639）；排行榜頁強制班級成員檢查（CWE-862）
- **點數改為班級範圍計算**：排行榜、點數管理頁、扣點/追回回應與上限杜絕跨班點數外洩（CWE-200）
- **排程規則請求驗證**：`schedule_type` 限定與各模式必填日期欄位，malformed 於持久化前回 422（CWE-20）

### Fixed（修正）

- 修復徽章管理頁面側邊欄顯示問題
- 修復 Milkdown 編輯器初始化問題
- 修復 DSL WASM 靜態檔案 404 錯誤
- 修復 CSV 匯入缺少錯誤訊息問題
- 修復 `.env` 與 Docker Compose 變數名稱不符問題
- **[P0]** 修復打卡流程崩潰問題（Codex Review P0）
- **[P0]** 修復共用 Modal 確認生命週期，恢復建立/加入班級功能
- **[P1]** 修復 `empty_state` macro 圖示被跳脫為原始碼
- **[P2]** 修復登入後 `next` 深層連結返回並硬化 open-redirect 防護
- 修復 SetupGuard middleware 未放行靜態資源前綴導致 setup 頁面失去樣式
- 升級 `fastapi-webpage` v0.2.1 → v0.3.1 並鎖定 tag

## [0.6.0] - 2026-04-01

### Added（新增）

- 新增 Rust DSL 表達式引擎（`crates/dsl-engine/`）— 支援 parse、validate、evaluate、autocomplete、hover、describe、help 七大 API，編譯為 WASM（前端）與 PyO3（後端）雙目標，共 46 個 Rust 單元測試
- 新增觸發規則管理系統（`src/gamification/triggers/`）— TriggerRule CRUD 五個 REST endpoints、教師管理頁面
- 新增 CodeMirror 6 DSL 編輯器 — 即時語法驗證、自動補全、hover 提示，整合 WASM module
- 新增 Milkdown WYSIWYG Markdown 徽章說明編輯器 — G2 分區塊模式（自動條件摘要 + 自由撰寫區）
- 新增 DSL Help Modal — 從 Rust crate 動態生成變數/運算子/函數/範例說明
- 新增 `GET /classes/{class_id}/students/stats` API — 班級學生聚合統計資料，支援時間窗口參數
- 新增前端規則 dry-run 測試 — WASM evaluate 逐一測試每位學生，顯示符合/不符合結果
- 新增 GitHub Actions CI for DSL engine（Rust 測試 → WASM 編譯 → PyO3 wheel 建置）
- 新增 `ensure_membership()` atomic upsert API — race-safe 的 ClassMembership 建立

### Changed（變更）

- Dockerfile 改為 multi-stage build — builder stage 編譯 PyO3 wheel，runtime stage 不含 Rust toolchain
- `ExtensionRegistry.get_all()` 回傳型別改為 `dict[str, Any]`，`deps.py` factory 函數自動轉為 list
- `review_join_request()` 新增 `class_id` 參數進行歸屬驗證
- `BadgeDefinition` 新增 `trigger_rule_id` 欄位，與 `trigger_key` 互斥（Pydantic model_validator）
- 觸發評估流程合併 code trigger + DSL rule 雙路徑

### Fixed（修正）

- **[P0]** 修復 `get_reward_providers()` 回傳 dict 導致打卡/繳交流程 `AttributeError` 崩潰
- 修復 join-request 跨班授權漏洞 — 教師無法再透過猜測 request_id 核准其他班級申請
- 修復 ClassMembership 重複建立問題 — 新增 unique compound index + 所有建立路徑 DuplicateKeyError 處理
- 修復 Discord override 欄位（`dc_title_override` 等）未傳遞至 webhook renderer
- 修復 `dsl_engine` 未安裝時 trigger-rule CRUD 回傳 500 — 改為明確錯誤訊息

### Security（安全性）

- ClassMembership `(class_id, user_id)` unique compound index 防止重複成員
- DSL 沙箱：白名單制變數與函數、無賦值/迴圈、class-scoped 資料隔離
- `ensure_membership()` 使用 MongoDB atomic upsert 防止 race condition
- join-request approval 改為 membership-first 順序，partial failure 可安全重試

## [0.5.0] - 2026-03-25

### Security（安全性）

- 修補跨班級授權漏洞 — 全面引入 Class-Scoped 授權檢查，防止 IDOR（Insecure Direct Object Reference，不安全的直接物件參考）攻擊（CWE-639 / CWE-863）
- 修復 7 項中等嚴重度安全漏洞（Security Audit R7–R13）：
  - 消除認證流程的 timing side-channel（計時旁路攻擊）漏洞（CWE-208）
  - 通用錯誤訊息取代內部細節輸出，防止資訊洩漏（CWE-209）
  - 新增密碼強度驗證 `validate_password_strength()`，最少 8 字元（CWE-521）
  - CSV 匯入加入 1MB 檔案大小上限，防止 DoS（Denial of Service，阻斷服務）攻擊（CWE-400）
  - 使用者建立/更新端點加入呼叫者權限上限檢查，防止權限提升（Privilege Escalation）（CWE-269）
  - Dockerfile 中 `FORWARDED_ALLOW_IPS` 預設改為不信任任何 Proxy（CWE-16）
- 實作 JWT 啟動強制檢查 — 生產環境使用預設密鑰時拒絕啟動
- 新增 CSRF（Cross-Site Request Forgery，跨站請求偽造）防護中介軟體，驗證 `Origin` / `Referer` 標頭
- 新增速率限制（Rate Limiting）— 登入端點 10 次/分鐘、密碼變更 5 次/分鐘、Setup 3 次/分鐘
- Cookie 加入 `Secure` 旗標，生產環境強制 HTTPS-only
- Docker 基礎設施認證強化 — MongoDB 加入 root 帳密、Redis 加入 `requirepass`、服務 port 綁定 `127.0.0.1`

### Added（新增）

- 新增 `slowapi` 依賴，用於 API 速率限制
- 新增 `CSRFMiddleware` 共用中介軟體模組
- 新增 `shared/limiter.py` 統一 SlowAPI Limiter 實例
- 新增安全性測試套件 — 速率限制、CSRF、Cookie Secure 旗標、Docker Compose 設定驗證（共 32+ 項測試）

### Changed（變更）

- Docker Compose 中 `mongo-express` 移至 `debug` profile，預設不啟動
- **Breaking Change**：Docker 部署需在 `.env` 設定 `MONGO_ROOT_PASSWORD` 與 `REDIS_PASSWORD`

## [0.3.0] - 2026-03-24

### Added（新增）

- **教師提交審閱系統** — 教師可審閱學生提交內容、執行積分追回
- **學生學習歷程頁面** — 學生可查看完整學習紀錄
- **個人設定頁面** — 新增使用者個人設定頁，支援 Gravatar 頭像顯示
- **建立帳號 email 必填驗證**
- **Discord Webhook 整合** — 任務指派時自動發送 Discord 通知
- **出席管理系統** — 出席管理後端 API 與前端介面
- **作業審查與補繳流程** — 包含 TaskSubmission 審查欄位與查重邏輯
- **學生 Sidebar 班級導覽** — 學生側邊欄顯示班級列表與切換
- **教師班級 Hub 頁面** — 含班級列表 Tab 切換與搜尋功能
- **教師管理介面重設計** — 共用 Page Context、側邊欄下拉選擇器、頁面 Layout 重構
- 補繳/審查頁面存取控制測試

### Changed（變更）

- 側邊欄管理入口精簡化
- 個人設定頁面 avatar 區塊美化
- 教師側邊欄重構，改用下拉式班級選擇器

### Fixed（修正）

- 修復儀表板（Dashboard）及多個頁面的 runtime bug 與 Spec 不符問題
- 將所有 Jinja2 範本中的硬編碼 URL 改為 `url_for()` 呼叫
- 修正 admin 班級列表 context 變數名稱衝突（`classes` → `class_list`）
- 修正側邊欄誤顯建班捷徑、header 跑版、班級卡片未顯示教師名稱
- 修正積分追回表單改用 AJAX 送出，避免 JSON API 端點收到 form-encoded 資料錯誤
- 修正新增班級按鈕錯誤行為
- 修補授權檢查缺口並同步 Security Spec 文件

### Security（安全性）

- 修補跨班級授權漏洞 — 全面引入 Class-Scoped 授權檢查（CWE-639 / CWE-863）

## [0.2.0] - 2026-03-19

### Added（新增）

- **System Setup Wizard（系統初始設定精靈）** — Redis 基礎設施、`SystemConfig` Document、lifespan 啟動檢查、Setup Wizard 路由與頁面
- **RBAC Permission Flags（角色型存取控制權限旗標）** — `Permission` IntFlag、Role Preset 常數、`require_permission` 授權守衛
- **role → permissions 資料遷移腳本**與整合測試
- **WebPage singleton 與 Pages 模組** — login / dashboard 頁面、PRG（Post/Redirect/Get）pattern
- **教師模板管理頁面**、簽到 PRG 流程、現有 page handler 遷移
- **SITE_ADMIN preset 與 SetupGuard middleware（中介軟體）** — dashboard 管理入口
- **Academic Pro 設計系統** — 設計系統基礎（CSS Variables、元件庫、Typography）
- **Dashboard 重新設計** — Widget Grid、班級卡片、Activity Feed（活動動態）、徽章條
- **任務提交頁面** — 遷移至 Toast UI Editor，實作混合欄位佈局
- **徽章頁面與任務模板列表**重新設計
- **教師頁面群與社群頁面群**重新設計
- **Admin Management Panel（管理員管理面板）** — API 端點、頁面路由與模板
- **Permission & Identity Refactor（權限與身分重構）** — 包含 `PERMISSION_SCHEMA` label / description、權限矩陣 UI
- **班級封存功能**，拆分 `ClassManager` 權限域
- **管理員班級列表頁、模板編輯 / 指派日期頁**
- **UI Polish（介面修飾）** — 多項介面微調與修正
- **Task Scheduling & Check-in（任務排程與簽到）** — 任務排程邏輯、教師簽到設定頁面
- Pages 模組整合測試

### Changed（變更）

- 以 `permissions` IntFlag 取代舊有 `role` 欄位，全面更新 User model 與 router 授權守衛
- Dashboard 管理入口與教師工具列 UI 重構
- Sidebar 管理工具擴充與優化

### Fixed（修正）

- 修正 `_register_extensions` 中 `AuthProvider` 未傳入 Protocol 型別的錯誤
- 修正 `templates_list.html` 缺少 `endblock` 標籤導致 content block 未關閉

## [0.1.0] - 2026-03-18

### Added（新增）

- **專案骨架初始化** — 建立 daily-training-submit-system 專案結構
- **基礎建設** — MongoDB 資料庫連線、Migration CLI（命令列介面）、Extension Registry（擴充套件註冊中心）
- **認證系統** — 本地帳號認證（Local Auth Provider）
- **班級管理** — 建立班級、加入班級、班級列表
- **任務系統** — 任務模板、任務指派、任務提交
- **簽到系統** — 每日簽到功能
- **遊戲化機制** — 積分（Points）、徽章（Badges）、排行榜（Leaderboard）、獎品預覽
- **社群牆** — 學生動態牆
- 完整規格文件（Spec）與變更提案（Change Proposal）
- README、使用說明、貢獻指南
- 專案重新命名為 DPRS（Daily Practice Report System）

[1.0.0]: https://github.com/fhcst/dprs/compare/v0.6.0...v1.0.0
[0.6.0]: https://github.com/fhcst/dprs/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/fhcst/dprs/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/fhcst/dprs/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fhcst/dprs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fhcst/dprs/releases/tag/v0.1.0
