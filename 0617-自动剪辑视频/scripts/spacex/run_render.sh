#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/spacex-promo"
OUTPUT_FILE="${ROOT_DIR}/outputs/spacex-promo-vertical.mp4"
LOG_FILE="${ROOT_DIR}/logs/spacex_render.log"

mkdir -p "${ROOT_DIR}/logs" "${ROOT_DIR}/outputs"
cd "${PROJECT_DIR}"

{
  echo "[spacex-render] $(date '+%Y-%m-%d %H:%M:%S')"
  npx hyperframes render --output "${OUTPUT_FILE}" --fps 30 --quality high
} 2>&1 | tee "${LOG_FILE}"
