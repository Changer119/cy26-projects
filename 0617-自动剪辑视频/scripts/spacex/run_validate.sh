#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/spacex-promo"
LOG_FILE="${ROOT_DIR}/logs/spacex_validate.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${PROJECT_DIR}"

{
  echo "[spacex-validate] $(date '+%Y-%m-%d %H:%M:%S')"
  npx hyperframes validate
} 2>&1 | tee "${LOG_FILE}"
