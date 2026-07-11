#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/wechat-karpathy-ppt-video"
LOG_FILE="${ROOT_DIR}/logs/wechat_karpathy_validate.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${PROJECT_DIR}"

{
  echo "[wechat-karpathy-validate] $(date '+%Y-%m-%d %H:%M:%S')"
  npx --yes hyperframes@0.6.110 validate
} 2>&1 | tee "${LOG_FILE}"
