#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/air-circulator-family-ad"
OUTPUT_FILE="${ROOT_DIR}/outputs/air-circulator-family-ad.mp4"
LOG_FILE="${ROOT_DIR}/logs/air_circulator_family_render.log"

mkdir -p "${ROOT_DIR}/logs" "${ROOT_DIR}/outputs"
cd "${PROJECT_DIR}"

{
  echo "[air-circulator-family-render] $(date '+%Y-%m-%d %H:%M:%S')"
  npx --yes hyperframes@0.6.110 render \
    --output "${OUTPUT_FILE}" --fps 30 --quality high
} 2>&1 | tee "${LOG_FILE}"
