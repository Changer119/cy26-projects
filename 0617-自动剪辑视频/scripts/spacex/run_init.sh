#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/spacex-promo"
LOG_FILE="${ROOT_DIR}/logs/spacex_init.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"

{
  echo "[spacex-init] $(date '+%Y-%m-%d %H:%M:%S')"
  if [ -f "${PROJECT_DIR}/index.html" ]; then
    echo "spacex-promo already initialized"
    exit 0
  fi
  if [ -d "${PROJECT_DIR}" ] && [ -z "$(find "${PROJECT_DIR}" -type f -print -quit)" ]; then
    find "${PROJECT_DIR}" -depth -type d -empty -delete
  fi
  npx hyperframes init spacex-promo --non-interactive
} 2>&1 | tee "${LOG_FILE}"
