#!/bin/bash
set -e

# ── 執行 database migration ─────────────────────────────────────────────────
echo "[entrypoint] 初始化 migration tracking collection..."
uv run python scripts/migrate.py init

echo "[entrypoint] 執行 pending migrations..."
uv run python scripts/migrate.py up

# ── 根據環境變數決定啟動模式 ─────────────────────────────────────────────────
# 同時接受 prod 與 production，與應用程式 is_production() 判定一致。
if [ "$FASTAPI_APP_ENVIRONMENT" = "prod" ] || [ "$FASTAPI_APP_ENVIRONMENT" = "production" ]; then
    echo "[entrypoint] 以 production 模式啟動"
    exec uv run fastapi run src/main.py "$@"
else
    echo "[entrypoint] 以 development 模式啟動"
    exec uv run fastapi dev src/main.py "$@" --host ${UVICORN_HOST} --port ${UVICORN_PORT}
fi
