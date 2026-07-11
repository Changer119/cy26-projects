#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/spacex-promo"
LOG_FILE="${ROOT_DIR}/logs/spacex_inspect.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${PROJECT_DIR}"

{
  echo "[spacex-inspect] $(date '+%Y-%m-%d %H:%M:%S')"
  npx hyperframes inspect --samples 12
} 2>&1 | tee "${LOG_FILE}"
