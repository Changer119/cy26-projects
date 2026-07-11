#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/wechat-karpathy-ppt-video"
OUTPUT_FILE="${ROOT_DIR}/outputs/wechat-karpathy-ppt-video.mp4"
LOG_FILE="${ROOT_DIR}/logs/wechat_karpathy_render.log"

mkdir -p "${ROOT_DIR}/logs" "${ROOT_DIR}/outputs"
cd "${PROJECT_DIR}"

{
  echo "[wechat-karpathy-render] $(date '+%Y-%m-%d %H:%M:%S')"
  npx --yes hyperframes@0.6.110 render --output "${OUTPUT_FILE}" --fps 30 --quality standard
} 2>&1 | tee "${LOG_FILE}"
