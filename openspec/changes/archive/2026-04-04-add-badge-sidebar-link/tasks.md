## 1. 加入徽章管理 sidebar 連結

- [x] 1.1 在 `src/templates/shared/base.html` 的 active class tool links 區塊（`{% if active_class.id %}` 內，「積分管理」連結之後）加入「徽章管理」導航連結，使用 `url_for('badges_manage_page', class_id=active_class.id)` 作為 href，圖示採用 Heroicons outline 風格的星形或獎章圖示，樣式與其他 class tool links 一致（Teacher sidebar includes badge management link）

## 2. 驗證

- [x] 2.1 啟動開發伺服器，以教師身分登入並確認 sidebar 顯示「徽章管理」連結、點擊後正確導向 badge 管理頁面、無 active class 時連結不顯示
