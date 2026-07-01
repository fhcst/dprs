## Summary

將專案版本從 0.2.0 更新至 0.3.0，反映自上次版本以來的所有新功能與安全修復。

## Motivation

自 0.2.0 以來，專案新增了大量功能與修復：
- 教師管理介面全面重構（側邊欄下拉選擇器、Breadcrumb、統計卡片、Filter Tabs）
- Discord Webhook 整合
- 作業審查/退回/補繳流程
- 出席管理功能
- 共用 Page Context Dependency
- 跨班級授權漏洞修補（CWE-639/CWE-863）
- 側邊欄管理入口精簡、個人設定頁面 Gravatar 連結

這些變更構成一個 minor version bump。

## Proposed Solution

- 更新 `pyproject.toml` 中的 `version` 從 `"0.2.0"` 到 `"0.3.0"`
- 產生 CHANGELOG / Release Note 摘要

## Impact

- 受影響的程式碼：`pyproject.toml`
