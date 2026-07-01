#!/usr/bin/env bash
# ==============================================================================
# scripts/backup.sh — DPRS MongoDB 備份（mongodump）
# ==============================================================================
# 透過執行中的 compose `mongo` container 跑 mongodump，輸出帶時間戳的 gzip
# archive 至 host 的 ./backups/。密碼一律讀環境變數（與 docker-compose 同一組），
# 不寫死於腳本內。
#
# 使用方式：
#   # 先確保 mongo 已啟動（docker compose up -d mongo），再執行：
#   scripts/backup.sh
#
# 認證來源（讀環境變數，可由 .env 提供）：
#   MONGO_ROOT_USERNAME  （預設 admin）
#   MONGO_ROOT_PASSWORD  （[必填] 無預設）
#   MONGO_DB_NAME        （預設 dts2）
#
# 輸出：
#   ./backups/dprs-<dbname>-YYYYmmdd-HHMMSS.archive.gz
#   重跑只會多產生一個新時間戳檔，不覆蓋既有備份（idempotent）。
#
# ── 還原（restore）────────────────────────────────────────────────────────────
# 將某個備份檔還原回執行中的 mongo（mongorestore，--drop 會先清掉同名 collection）。
# mongo container 內已有 MONGO_INITDB_ROOT_USERNAME / MONGO_INITDB_ROOT_PASSWORD
# 環境變數（由 compose 注入），故可在 container 內直接引用、host 端不需露出密碼：
#
#   docker compose exec -T mongo sh -c \
#     'mongorestore --username "$MONGO_INITDB_ROOT_USERNAME" \
#        --password "$MONGO_INITDB_ROOT_PASSWORD" \
#        --authenticationDatabase admin --gzip --archive --drop' \
#     < ./backups/dprs-<dbname>-YYYYmmdd-HHMMSS.archive.gz
#
# 或在已安裝 mongo tools 的 host 上，對外露的 127.0.0.1:27017 還原
# （先 `source .env` 取得 MONGO_ROOT_PASSWORD）：
#   mongorestore --host 127.0.0.1 --port 27017 \
#     --username "$MONGO_ROOT_USERNAME" --password "$MONGO_ROOT_PASSWORD" \
#     --authenticationDatabase admin --gzip \
#     --archive=./backups/dprs-<dbname>-YYYYmmdd-HHMMSS.archive.gz --drop
# ==============================================================================

set -euo pipefail

# ── 專案根目錄（本腳本位於 scripts/ 之下）─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# ── 載入 .env（若存在）以取得認證；不覆蓋已存在的環境變數 ────────────────────
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# ── 解析認證（皆讀環境變數，密碼不寫死）───────────────────────────────────────
MONGO_ROOT_USERNAME="${MONGO_ROOT_USERNAME:-admin}"
MONGO_DB_NAME="${MONGO_DB_NAME:-dts2}"

if [[ -z "${MONGO_ROOT_PASSWORD:-}" ]]; then
    echo "error: 環境變數 MONGO_ROOT_PASSWORD 未設定（請於 .env 或環境提供）" >&2
    exit 1
fi

# ── 確保輸出目錄存在（idempotent）─────────────────────────────────────────────
BACKUP_DIR="${PROJECT_ROOT}/backups"
mkdir -p "${BACKUP_DIR}"

# ── 時間戳檔名 ────────────────────────────────────────────────────────────────
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTFILE="${BACKUP_DIR}/dprs-${MONGO_DB_NAME}-${TIMESTAMP}.archive.gz"

echo "[backup] 對 compose mongo 執行 mongodump → ${OUTFILE}"

# ── 在 mongo container 內跑 mongodump，archive 串流導回 host 檔案 ─────────────
# 透過 docker compose exec -T，將 --archive 寫到 stdout 再重導向至 host。
# 認證一律引用「compose 已注入 container」的環境變數（MONGO_INITDB_ROOT_USERNAME /
# MONGO_INITDB_ROOT_PASSWORD / MONGO_INITDB_DATABASE），於 container 內展開——
# 密碼完全留在 container 環境，不經由 `-e KEY=VALUE` 進入 host 端 `docker compose
# exec` 的 argv（避免 ps aux / /proc/<pid>/cmdline 在備份期間外洩 root 密碼）。
# 重導向會在指令執行前就建立（截斷）OUTFILE。若 mongodump/exec 失敗，set -e 會
# 在抵達下方完整性檢查前就中止腳本，於是留下誤導性的 0-byte .archive.gz。以 ERR trap
# 在失敗當下清掉半成品；成功後再解除 trap，讓既有完整性檢查接手。
trap 'rm -f "${OUTFILE}"' ERR

docker compose exec -T \
    mongo \
    sh -c 'mongodump \
        --username "$MONGO_INITDB_ROOT_USERNAME" \
        --password "$MONGO_INITDB_ROOT_PASSWORD" \
        --authenticationDatabase admin \
        --db "$MONGO_INITDB_DATABASE" \
        --archive --gzip --quiet' \
    > "${OUTFILE}"

trap - ERR

# ── 基本完整性檢查：檔案存在且非空 ────────────────────────────────────────────
if [[ ! -s "${OUTFILE}" ]]; then
    echo "error: 備份檔為空，mongodump 可能失敗：${OUTFILE}" >&2
    rm -f "${OUTFILE}"
    exit 1
fi

echo "[backup] 完成：${OUTFILE} ($(du -h "${OUTFILE}" | cut -f1))"
echo "[backup] 還原：mongorestore --gzip --archive=${OUTFILE} --drop（詳見本檔 header）"
