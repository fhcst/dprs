## Context

專案使用 Semantic Versioning。目前為 0.2.0，需要 bump 到 0.3.0 以反映新功能。

## Goals / Non-Goals

**Goals:**
- 更新 pyproject.toml 中的版本號
- 產生 Release Note

**Non-Goals:**
- Git tag（由 CI/CD 或手動處理）
- Docker image 版本更新

## Decisions

### 僅更新 pyproject.toml 版本號

版本號集中在 `pyproject.toml` 的 `version` 欄位，無需同步更新其他檔案。

## Risks / Trade-offs

無。純版本號更新。
