#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME="wechat-karpathy-ppt-video"
LOG_FILE="${ROOT_DIR}/logs/wechat_karpathy_init.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"

{
  echo "[wechat-karpathy-init] $(date '+%Y-%m-%d %H:%M:%S')"
  if [[ -d "${PROJECT_NAME}" ]]; then
    echo "project already exists: ${PROJECT_NAME}"
  else
    npx --yes hyperframes@0.6.110 init "${PROJECT_NAME}" --non-interactive
  fi
} 2>&1 | tee "${LOG_FILE}"
